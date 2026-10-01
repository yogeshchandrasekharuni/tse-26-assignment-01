"""Versioned agents-as-tools gateway with JSON intents and exact Fast Agent playback."""

import asyncio
import json
import os
from importlib.metadata import version
from pathlib import Path
from typing import Literal, cast

from fast_agent import FastAgent, Prompt
from fast_agent.agents.agent_types import FunctionToolConfig
from fast_agent.agents.llm_agent import LlmAgent
from fast_agent.agents.tool_runner import ToolRunner, ToolRunnerHooks
from fast_agent.constants import FAST_AGENT_ERROR_CHANNEL
from fast_agent.llm.internal.playback import PlaybackLLM
from fast_agent.llm.provider.openai.llm_openai import OpenAILLM
from fast_agent.types import PromptMessageExtended, RequestParams
from mcp_types import TextContent
from openai import AsyncOpenAI
from pydantic import JsonValue, TypeAdapter

from housing.agents.context import context_upper_bound, require_context_budget
from housing.contracts.common import FrozenModel
from housing.contracts.decisions import (
    FinalizeDecision,
    PlanDecision,
    PriceDecision,
    RegionDecision,
    ReportDecision,
    ReviewDecision,
    SupplyDecision,
)
from housing.contracts.errors import HousingError
from housing.identity import ROOT, canonical_json, semantic_hash, write_json
from housing.replay.capture import load_cassettes, save_cassette, semantic_message
from housing.workflow.controller import Controller, Role

ROLES: tuple[Role, ...] = ("orchestrator", "price", "supply", "region", "reviewer", "composer")
SCHEMAS: dict[str, type[FrozenModel]] = {
    "orchestrator": PlanDecision,
    "price": PriceDecision,
    "supply": SupplyDecision,
    "region": RegionDecision,
    "reviewer": ReviewDecision,
    "composer": ReportDecision,
}
CONFIG = ROOT / "configs/production-v4.yaml"
JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
OBJECTIVE = (
    "Analyze the trusted controller-bound request through your internal agents. "
    "Submit the current constrained plan, delegate the active specialists, then reviewer. "
    "Follow genuine feedback. After acceptance delegate composer, finalize, and return the exact acknowledgement."
)


def prompt_bundle() -> dict[str, str]:
    return {
        role: (ROOT / "prompts/v3" / f"{role}.md").read_text()
        + "\nDecision schema:\n"
        + canonical_json(SCHEMAS[role].model_json_schema())
        + (
            "\nFinalization schema:\n" + canonical_json(FinalizeDecision.model_json_schema())
            if role == "orchestrator"
            else ""
        )
        for role in ROLES
    }


def disable_sdk_retries(llm: OpenAILLM) -> None:
    """Pinned 0.10.45 compatibility: SDK=0, framework=one retry per request, including clones."""
    original = llm._openai_client

    def zero_retry_client() -> AsyncOpenAI:
        client = original()
        client.max_retries = 0
        return client

    llm._openai_client = zero_retry_client  # type: ignore[method-assign]
    llm.retry_count = 1
    llm.retry_backoff_seconds = 0.1


class FastAgentOrchestrator:
    def __init__(self, controller: Controller, boundary_hash: str, replay_source: Path | None = None):
        if version("fast-agent-mcp") != "0.10.45":
            raise HousingError("TOOL_ERROR", "Gateway requires locked Fast Agent 0.10.45", "startup")
        self.controller, self.boundary_hash = controller, boundary_hash
        self.instructions = prompt_bundle()
        self.replay_source = replay_source
        self.packets = load_cassettes(replay_source) if replay_source else ()
        self.sequence = 0
        self.pending: dict[ToolRunner, tuple[int, dict[str, JsonValue]]] = {}
        self.prepared: set[ToolRunner] = set()
        self.finalization_prepared: set[ToolRunner] = set()
        self.playback_loaded: list[PlaybackLLM] = []
        self.configured_llms: list[OpenAILLM] = []

    @property
    def runtime_model(self) -> str:
        return "playback" if self.replay_source else f"housing-v4-s{self.controller.request.seed}"

    def parent_tools(self) -> list[FunctionToolConfig]:
        controller = self.controller

        def inspect_context(section: Literal["current"]) -> dict[str, object]:
            """Read the trusted immutable query, current state, receipts, constraints and evidence."""
            if controller.fatal:
                raise controller.fatal
            return controller.context()

        def plan_scan(decision_json: str) -> dict[str, object]:
            """Apply your strict PlanDecision. Match the current planning_constraints; never change the query."""
            return controller.submit("orchestrator", decision_json)

        return [inspect_context, plan_scan]

    @staticmethod
    def role(agent: LlmAgent) -> Role:
        name = agent.name.split("[", 1)[0]
        if name not in ROLES:
            raise HousingError("AGENT_POLICY_ERROR", "Unknown agent identity", "gateway")
        return cast(Role, name)

    async def before(self, runner: ToolRunner, messages: list[PromptMessageExtended]) -> None:
        if self.controller.fatal:
            raise self.controller.fatal
        agent = runner.agent
        if not isinstance(agent, LlmAgent):
            raise HousingError("TOOL_ERROR", "Unexpected runner type", "capture")
        role = self.role(agent)
        if runner not in self.prepared:
            messages.append(
                Prompt.user(canonical_json({"trusted_role": role, "state": self.controller.context()}))
            )
            self.prepared.add(runner)
        finalizing = role == "orchestrator" and self.controller.stage == "COMPOSED"
        if finalizing:
            # Pinned ToolRunner seam: suppress native tools for the typed terminal decision.
            runner._tools = []
            if runner.request_params:
                runner.request_params.sampling_tool_choice = "none"
            if runner not in self.finalization_prepared:
                messages.append(
                    Prompt.user(
                        canonical_json(
                            {
                                "task": "Return FinalizeDecision only; no native tool calls",
                                "schema": FinalizeDecision.model_json_schema(),
                                "state": self.controller.context(),
                            }
                        )
                    )
                )
                self.finalization_prepared.add(runner)
        llm = agent._llm
        if isinstance(llm, OpenAILLM) and llm not in self.configured_llms:
            disable_sdk_retries(llm)
            self.configured_llms.append(llm)
        seq = self.sequence
        self.sequence += 1
        if self.sequence > 70:
            self.controller.abort("Analysis exceeded 70 model decisions", "BUDGET_EXCEEDED")
        tools = (await agent.list_tools()).model_dump(mode="json", exclude_none=True)
        if finalizing:
            tools["tools"] = []
        raw_messages = [m.model_dump(mode="json", exclude_none=True) for m in messages]
        payload = JSON_OBJECT.validate_json(
            canonical_json(
                {
                    "normalization_version": "production-semantic-2",
                    "agent": agent.name,
                    "messages": raw_messages,
                    "message_tool_call_order": [list(m.tool_calls or {}) for m in messages],
                    "tools": tools,
                    "instruction": agent.instruction,
                    "context": self.controller.context(),
                    "model_profile": f"housing-v4-s{self.controller.request.seed}",
                    "requested_seed": self.controller.request.seed,
                    "effective_seed": self.controller.request.seed,
                    "role_schema_sha256": semantic_hash(SCHEMAS[role].model_json_schema()),
                    "prompt_bundle_sha256": semantic_hash(self.instructions),
                    "boundary_sha256": self.boundary_hash,
                    "retry_policy": {"framework_retries": 1, "sdk_retries": 0},
                }
            )
        )
        bound = context_upper_bound(
            agent.instruction, [JSON_OBJECT.validate_python(m) for m in raw_messages], tools
        )
        require_context_budget(bound)
        self.pending[runner] = (seq, payload)
        write_json(self.controller.directory / "model" / f"{seq:03d}.input.json", payload)
        write_json(
            self.controller.directory / "model" / f"{seq:03d}.budget.json", {"upper_bound_tokens": bound}
        )
        if self.replay_source:
            if seq >= len(self.packets):
                raise HousingError(
                    "REPLAY_MISS", "Capture exhausted before current decision", "capture_match"
                )
            packet = self.packets[seq]
            packet.verify(payload, self.boundary_hash)
            if not isinstance(llm, PlaybackLLM):
                raise HousingError("REPLAY_MISS", "Replay must use Fast Agent PlaybackLLM", "playback")
            if llm not in self.playback_loaded:
                responses = []
                for p in self.packets:
                    # Detached names repeat across parent turns (reviewer[1], etc.).
                    # Each child clone has exactly one JSON decision. Only the parent
                    # owns a multi-call response queue; never reuse an older child's answer.
                    if (role != "orchestrator" and p.sequence != seq) or p.input["agent"] != agent.name:
                        continue
                    recorded = PromptMessageExtended.model_validate(p.response)
                    if recorded.tool_calls:
                        recorded.tool_calls = {
                            key: recorded.tool_calls[key] for key in p.response_tool_call_order
                        }
                    responses.append(recorded)
                loaded = await llm.generate(responses)
                if not loaded.first_text().startswith("HISTORY LOADED"):
                    raise HousingError("REPLAY_MISS", "Playback initialization failed", "playback")
                self.playback_loaded.append(llm)

    async def after(self, runner: ToolRunner, message: PromptMessageExtended) -> None:
        seq, payload = self.pending.pop(runner)
        raw = JSON_OBJECT.validate_python(message.model_dump(mode="json", exclude_none=True))
        write_json(self.controller.directory / "model" / f"{seq:03d}.response.json", raw)
        if self.replay_source and semantic_hash(semantic_message(raw)) != semantic_hash(
            semantic_message(self.packets[seq].response)
        ):
            raise HousingError(
                "REPLAY_MISS", "Playback returned a different captured response", "playback_response"
            )
        if not self.replay_source:
            save_cassette(self.controller.directory, seq, self.boundary_hash, payload, raw)
        if message.channels and FAST_AGENT_ERROR_CHANNEL in message.channels:
            details = canonical_json(message.channels[FAST_AGENT_ERROR_CHANNEL])
            parse_error = any(
                marker in details
                for marker in (
                    "XML syntax error",
                    "expected element type <function>",
                    "tool call parsing failed",
                )
            )
            error = HousingError(
                "AGENT_OUTPUT_INVALID" if parse_error else "MODEL_UNAVAILABLE",
                "Provider rejected model tool-call syntax"
                if parse_error
                else "Provider failed after its declared transport retry",
                "provider_tool_parse" if parse_error else "inference",
            )
            self.controller.fatal = error
            raise error
        agent = runner.agent
        if not isinstance(agent, LlmAgent):
            raise HousingError("TOOL_ERROR", "Unexpected runner", "dispatch")
        role = self.role(agent)
        if role != "orchestrator":
            if message.tool_calls:
                self.controller.abort("Specialists may emit only their JSON intent", "AGENT_OUTPUT_INVALID")
            result = self.controller.submit(role, message.first_text())
            # Preserve raw model output above. The parent receives the current verified dispatcher result.
            message.content = [TextContent(type="text", text=canonical_json(result))]
            write_json(self.controller.directory / "model" / f"{seq:03d}.dispatched.json", result)
        elif not message.tool_calls:
            result = self.controller.submit_finalization(message.first_text())
            message.content = [TextContent(type="text", text=canonical_json(result))]
            write_json(self.controller.directory / "model" / f"{seq:03d}.dispatched.json", result)

    async def before_tool(self, runner: ToolRunner, message: PromptMessageExtended) -> None:
        agent = runner.agent
        if not isinstance(agent, LlmAgent) or self.role(agent) != "orchestrator":
            self.controller.abort("Only the parent may invoke agent/native control tools")
            return
        for call in (message.tool_calls or {}).values():
            tool, args = call.params.name, call.params.arguments or {}
            if tool == "inspect_context" and args != {"section": "current"}:
                self.controller.abort("inspect_context requires section=current", "AGENT_OUTPUT_INVALID")
            if tool == "plan_scan" and (
                set(args) != {"decision_json"} or not isinstance(args.get("decision_json"), str)
            ):
                self.controller.abort("plan_scan requires one decision_json string", "AGENT_OUTPUT_INVALID")
            if tool == "inspect_context":
                continue
            if tool.startswith("agent__"):
                child = tool.removeprefix("agent__")
                if child not in ROLES[1:]:
                    self.controller.abort("Unknown child agent")
                self.controller.guard(cast(Role, child))
            elif tool == "plan_scan":
                self.controller.guard("orchestrator")
            else:
                self.controller.abort("Tool is outside the parent's capabilities")

    async def guarded_before(self, runner: ToolRunner, messages: list[PromptMessageExtended]) -> None:
        try:
            await self.before(runner, messages)
        except HousingError as error:
            self.controller.fatal = error
            raise

    async def guarded_after(self, runner: ToolRunner, message: PromptMessageExtended) -> None:
        try:
            await self.after(runner, message)
        except HousingError as error:
            self.controller.fatal = error
            raise

    async def after_tools(self, runner: ToolRunner, message: PromptMessageExtended) -> None:
        if self.controller.fatal:
            raise self.controller.fatal
        if any(result.is_error for result in (message.tool_results or {}).values()):
            # Unexpected framework/child transport failures are infrastructure errors,
            # not a subsequent model policy fault caused by an incomplete scan.
            self.controller.fatal = HousingError(
                "TOOL_ERROR",
                "Framework tool/child execution failed; see preserved tool response",
                "child_execution",
            )
            write_json(self.controller.directory / "framework-tool-failure.json", message)
            raise self.controller.fatal

    async def run(self) -> None:
        os.environ["FAST_AGENT_HOME"] = str(ROOT / "configs/fast-agent-home")
        fast = FastAgent(
            "housing-analysis",
            config_path=str(CONFIG),
            parse_cli_args=False,
            quiet=True,
            isolated=True,
            home=str(ROOT / "configs/fast-agent-home"),
        )

        async def definition() -> None:
            pass

        for role in ROLES[1:]:
            fast.agent(
                name=role,
                instruction=self.instructions[role],
                model=self.runtime_model,
                use_history=False,
                skills=[],
                function_tools=[],
                request_params=RequestParams(
                    max_tokens=1024, use_history=False, max_iterations=1, streaming_timeout=60
                ),
            )(definition)
        fast.agent(
            name="orchestrator",
            instruction=self.instructions["orchestrator"],
            agents=list(ROLES[1:]),
            model=self.runtime_model,
            use_history=False,
            skills=[],
            function_tools=self.parent_tools(),
            history_source="none",
            history_merge_target="none",
            max_parallel=1,
            child_timeout_sec=90,
            request_params=RequestParams(
                max_tokens=1024,
                use_history=False,
                max_iterations=28,
                parallel_tool_calls=False,
                streaming_timeout=60,
            ),
        )(definition)
        async with fast.run() as agents:
            for role in ROLES:
                agent = agents[role]
                if not isinstance(agent, LlmAgent):
                    raise HousingError("TOOL_ERROR", "Unexpected agent type", "startup")
                agent.tool_runner_hooks = ToolRunnerHooks(
                    before_llm_call=self.guarded_before,
                    after_llm_call=self.guarded_after,
                    before_tool_call=self.before_tool,
                    after_tool_call=self.after_tools,
                )
            response = await asyncio.wait_for(agents.orchestrator.send(OBJECTIVE), timeout=600)
            if self.controller.repair_role == "orchestrator" and self.controller.stage == "COMPOSED":
                response = await asyncio.wait_for(
                    agents.orchestrator.send(
                        "Correct the recorded schema_repair for finalization. Return FinalizeDecision only."
                    ),
                    timeout=90,
                )
        write_json(self.controller.directory / "parent-response.json", {"response": response})
        if self.controller.fatal:
            raise self.controller.fatal
        if self.replay_source and self.sequence != len(self.packets):
            raise HousingError("REPLAY_MISS", "Capture contains unconsumed decisions", "playback")
        output = self.controller.output
        if output is None:
            raise HousingError("AGENT_OUTPUT_INVALID", "Parent stopped before finalization", "parent_return")
        try:
            actual = json.loads(response)
        except ValueError as error:
            raise HousingError(
                "AGENT_OUTPUT_INVALID", "Parent must return its exact JSON acknowledgement", "parent_return"
            ) from error
        if actual != {
            "status": "completed",
            "canonical_sha256": semantic_hash(output.canonical),
            "total_observations": output.canonical.summary.total_observations,
        }:
            raise HousingError(
                "AGENT_OUTPUT_INVALID", "Parent acknowledgement differs from finalization", "parent_return"
            )
