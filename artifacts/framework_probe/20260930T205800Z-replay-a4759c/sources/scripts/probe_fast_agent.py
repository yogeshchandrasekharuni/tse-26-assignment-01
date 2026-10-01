"""Live framework proof and strict offline playback. Never headline campaign evidence."""

import argparse
import asyncio
import hashlib
import inspect
import json
import os
import platform
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from fast_agent import FastAgent, load_prompt
from fast_agent.types import RequestParams
from pydantic import BaseModel, ConfigDict, ValidationError

from probe_support import Evidence, RecordingProxy, canonical, deny_network, digest, match_cassette, write_json
from probe_tools import ProbeTools

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (104729, 130363, 155921)
INSTRUCTION = "PROBE_ROLE=price. Return only one JSON object matching this schema: "


class PriceIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    role: Literal["price"]
    decision_type: Literal["tool_intent"]
    tool: Literal["price_stats"]
    partition_order: Literal["month_asc", "zip_asc"]
    purpose: Literal["statistics"]


def fast_instance(config: Path) -> FastAgent:
    return FastAgent("housing-environment-proof", config_path=str(config), parse_cli_args=False,
                     quiet=True, isolated=True, home=str(ROOT / "configs/fast-agent-home"))


def register(fast: FastAgent, name: str, instruction: str, model: str, tools: list | None = None) -> None:
    async def definition():
        pass
    fast.agent(name=name, instruction=instruction, model=model, use_history=False, skills=[],
               function_tools=tools or [], request_params=RequestParams(
                   max_tokens=1024, use_history=False, max_iterations=6, streaming_timeout=60))(definition)


def model_identity(seed: int) -> dict:
    manifest = json.loads((ROOT / "configs/model_manifest.json").read_text())
    name = f"housing-qwen-s{seed}:latest"
    model = next(t for t in manifest["tags"]["models"] if t["name"] == name)
    profile = next(p for p in manifest["profiles"] if p["seed"] == seed)
    assert f"seed                           {seed}" in profile["show"]["parameters"]
    return {"seed": seed, "wire_model": name.removesuffix(":latest"), "digest": model["digest"]}


def make_basis(seed: int, prompt: str, instruction: str) -> dict:
    return {"purpose": "framework_probe_not_campaign", "role": "price", "iteration": 0,
            "semantic_prompt": prompt, "instruction": instruction,
            "schema_sha256": digest(PriceIntent.model_json_schema()),
            "overlay_sha256": hashlib.sha256((ROOT / f"configs/fast-agent-home/model-overlays/housing-s{seed}.yaml").read_bytes()).hexdigest(),
            "dependency_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            "framework_config_sha256": hashlib.sha256((ROOT / "configs/fast-agent.yaml").read_bytes()).hexdigest(),
            "tool_bundle_sha256": hashlib.sha256((ROOT / "scripts/probe_tools.py").read_bytes()).hexdigest(),
            "fixture_sha256": hashlib.sha256((ROOT / "housing-tse-codex-handoff/fixtures/low_support.csv").read_bytes()).hexdigest(),
            "model": model_identity(seed), "fast_agent": version("fast-agent-mcp")}


async def capture_decisions(evidence: Evidence, config: Path, proxy: RecordingProxy) -> list[str]:
    cassette_dir = evidence.directory / "cassettes"
    cassette_dir.mkdir()
    keys = []
    instruction = INSTRUCTION + canonical(PriceIntent.model_json_schema())
    for seed in SEEDS:
        fast = fast_instance(config)
        register(fast, "price", instruction, f"housing-s{seed}")
        register(fast, "supply", "PROBE_ROLE=supply. Return only {\"role\":\"supply\"}.", f"housing-s{seed}")
        prompt = canonical({"request": "request price_stats for the controller-bound selection",
                            "context_marker": f"source-only-{seed}", "allowed_orders": ["month_asc", "zip_asc"]})
        start_index = len(proxy.requests)
        async with fast.run() as agents:
            response = await asyncio.wait_for(agents.price.send(prompt), 90)
            basis = make_basis(seed, prompt, instruction)
            key = digest(basis)
            cassette = {"origin": "live_captured", "key_basis": basis, "raw_response_text": response,
                        "raw_response_sha256": hashlib.sha256(response.encode()).hexdigest(),
                        "capture_attempt": evidence.directory.name, "captured_at_utc": datetime.now(UTC).isoformat()}
            write_json(cassette_dir / f"{key}.json", cassette)
            intent = PriceIntent.model_validate_json(response)
            receipt = ProbeTools(evidence).scan_price()
            write_json(evidence.directory / f"decision-{seed}.json",
                       {"intent": intent.model_dump(), "tool_receipt": receipt, "cassette_key": key})
            # Check a second turn on the same role and a different role for leaked source history.
            second = await asyncio.wait_for(agents.price.send(
                "Request price_stats for a fresh follow-up selection. Return permitted JSON only."), 90)
            PriceIntent.model_validate_json(second)
            supply = await asyncio.wait_for(agents.supply.send("Return your supply role JSON only."), 90)
            assert json.loads(supply) == {"role": "supply"}
        wires = proxy.requests[start_index:]
        assert len(wires) == 3
        for wire in wires:
            assert wire["model"] == model_identity(seed)["wire_model"]
            assert wire.get("seed") in (None, seed)
            assert wire.get("reasoning_effort") == "none"
            assert len([m for m in wire["messages"] if m["role"] == "user"]) == 1
        assert f"source-only-{seed}" not in canonical(wires[1]["messages"])
        assert f"source-only-{seed}" not in canonical(wires[2]["messages"])
        evidence.log("SEED_AND_ISOLATION_VERIFIED", seed=seed, cassette_key=key,
                     seed_support="verified_model_default_best_effort_sampling", wire_requests=len(wires))
        keys.append(key)
    invalid = {"role": "price", "decision_type": "tool_intent", "tool": "price_stats",
               "partition_order": "month_asc", "purpose": "statistics", "price_min_cents": 0}
    try:
        PriceIntent.model_validate(invalid)
    except ValidationError:
        evidence.log("FORBIDDEN_FILTER_CHANGE_REJECTED")
    else:
        raise AssertionError("Unknown fields accepted")
    return keys


async def replay_decisions(evidence: Evidence, config: Path, capture: Path) -> dict:
    index = json.loads((capture / "decision-index.json").read_text())
    receipts = []
    with deny_network() as network_attempts:
        import socket
        try:
            socket.create_connection(("127.0.0.1", 11434))
        except OSError:
            network_attempts.clear()  # intentional test of the blocker itself
        else:
            raise AssertionError("Network blocker failed")
        for seed, key in zip(SEEDS, index["cassette_keys"], strict=True):
            saved = json.loads((capture / "cassettes" / f"{key}.json").read_text())
            basis = make_basis(seed, saved["key_basis"]["semantic_prompt"],
                               INSTRUCTION + canonical(PriceIntent.model_json_schema()))
            cassette = match_cassette(capture / "cassettes", basis)
            for field in ["semantic_prompt", "schema_sha256", "tool_bundle_sha256", "fixture_sha256",
                          "overlay_sha256", "dependency_lock_sha256", "framework_config_sha256", "model"]:
                try:
                    match_cassette(capture / "cassettes", {**basis, field: "deliberately-changed"})
                except ValueError as error:
                    assert "REPLAY_MISS" in str(error)
                else:
                    raise AssertionError(f"Changed {field} replayed")
            conversation = evidence.directory / f"conversation-{seed}.txt"
            conversation.write_text("---USER\n" + basis["semantic_prompt"] + "\n---ASSISTANT\n" +
                                    cassette["raw_response_text"] + "\n")
            fast = fast_instance(config)
            register(fast, "price", basis["instruction"], "playback")
            async with fast.run() as agents:
                loaded = await agents.price.generate(load_prompt(conversation))
                assert loaded.first_text().startswith("HISTORY LOADED")
                replayed = await agents.price.send(basis["semantic_prompt"])
                assert replayed == cassette["raw_response_text"]
                PriceIntent.model_validate_json(replayed)
                receipt = ProbeTools(evidence).scan_price()
            reference = json.loads((capture / f"decision-{seed}.json").read_text())["tool_receipt"]
            assert receipt == reference
            receipts.append(receipt["receipt_sha256"])
            evidence.log("PLAYBACK_AND_TOOL_VERIFIED", seed=seed, cassette_key=key,
                         tool_receipt_sha256=receipt["receipt_sha256"])
        assert not network_attempts, network_attempts
    return {"status": "passed", "capture": str(capture.relative_to(ROOT)), "decisions_replayed": 3,
            "tools_reexecuted": 3, "semantic_mismatch_tests": 24, "network_attempts": 0,
            "receipt_hashes": receipts}


async def native_orchestration(evidence: Evidence, config: Path, engine: str = "native") -> dict:
    tools = ProbeTools(evidence)
    fast = fast_instance(config)
    model = "housing-s104729"

    # Detached child clones deepcopy configuration. Plain function closures keep per-run
    # tool bindings without deepcopying the evidence writer's non-pickleable thread lock.
    def scan_price() -> dict:
        """Run the current controller-bound exact price scan once and return its receipt."""
        return tools.scan_price()

    def scan_supply() -> dict:
        """Count the current controller-bound selection and check index completeness."""
        return tools.scan_supply()

    def scan_region() -> dict:
        """Diagnose the requested ZIP after REFINE activates Region. Never change filters."""
        return tools.scan_region()

    def inspect_coverage() -> dict:
        """Read actual specialist receipts before submitting a review decision."""
        return tools.inspect_coverage()

    def submit_review(decision: Literal["REFINE", "ACCEPT_LIMITED"],
                      requested_action: Literal["EXACT_RESCAN_WITH_REGION"] | None = None) -> dict:
        """Submit REFINE with EXACT_RESCAN_WITH_REGION for indexed mismatch;
        submit ACCEPT_LIMITED with null for authoritative confirmed sparse support."""
        return tools.submit_review(decision, requested_action)

    def compose_report(fact_ids: list[Literal["observations", "support"]]) -> dict:
        """Select observations and support facts after acceptance; return the grounded report."""
        return tools.compose_report(fact_ids)

    register(fast, "price", "PROBE_ROLE=price. Price specialist: for each assigned task call scan_price "
             "exactly once and return its JSON receipt. Never invent numbers.", model, [scan_price])
    register(fast, "supply", "PROBE_ROLE=supply. Supply specialist: for each assigned task call scan_supply "
             "exactly once and return its JSON receipt. Never infer counts.", model, [scan_supply])
    register(fast, "region", "PROBE_ROLE=region. Conditional Region specialist: when assigned a coverage "
             "diagnostic call scan_region once and return its JSON receipt.", model, [scan_region])
    register(fast, "reviewer", "PROBE_ROLE=reviewer. First inspect_coverage, then submit_review. Indexed "
             "INDEX_COVERAGE_MISMATCH requires REFINE and EXACT_RESCAN_WITH_REGION. Full_csv confirmed "
             "sparsity requires ACCEPT_LIMITED and null requested_action. Return submit_review JSON.",
             model, [inspect_coverage, submit_review])
    register(fast, "composer", "PROBE_ROLE=composer. After acceptance, call compose_report with fact_ids "
             "[observations,support] and return its JSON exactly. Never recalculate statistics.",
             model, [compose_report])

    async def orchestrator():
        pass

    parent_instruction = (
        "PROBE_ROLE=orchestrator. You alone receive requests and return final responses. "
        "Delegate per the objective, actual receipts and reviewer feedback. Never fabricate tool results or "
        "replace specialists. Region is forbidden before REFINE. Completion requires the composer report. "
        "Return the composer's report to the caller."
    )
    children = ["price", "supply", "region", "reviewer", "composer"]
    if engine == "native":
        fast.orchestrator(name="orchestrator", agents=children,
                          instruction=parent_instruction + " Available agents: {{agents}}.",
                          model=model, plan_type="iterative", plan_iterations=7, use_history=False,
                          request_params=RequestParams(max_tokens=1024, use_history=False,
                                                       streaming_timeout=60))(orchestrator)
    else:
        fast.agent(name="orchestrator", agents=children, instruction=parent_instruction,
                   model=model, use_history=False, skills=[], history_source="none", history_merge_target="none",
                   max_parallel=1, child_timeout_sec=90,
                   request_params=RequestParams(max_tokens=1024, use_history=False, max_iterations=12,
                                                parallel_tool_calls=False, streaming_timeout=60))(orchestrator)

    objective = ("Run the labeled synthetic index-omission probe with immutable query. First delegate indexed "
                 "scans to price and supply. Next delegate coverage review to reviewer. If reviewer returns REFINE, "
                 "replan: delegate new full_csv scans to price and supply AND activate region for diagnostics; "
                 "then ask reviewer again. Only after ACCEPT_LIMITED delegate report to composer. Every role must "
                 "call its real tool. Return composer's report through this Orchestrator. Completion requires "
                 "both review decisions and the report. Region must not run in the first pass.")
    start = time.monotonic()
    async with fast.run() as agents:
        response = await asyncio.wait_for(agents.orchestrator.send(objective), 600)
        write_json(evidence.directory / "native-response.json", {"response": response})
    assert tools.refinements == 1, tools.reviews
    assert [r["decision"] for r in tools.reviews] == ["REFINE", "ACCEPT_LIMITED"], tools.reviews
    assert tools.accepted and tools.report and tools.report["total_observations"] == 24
    assert tools.query_hash == digest(tools.query)
    actual = [(e["role"], e["strategy"]) for e in evidence.events if e["event"] == "TOOL_COMPLETED"]
    for pair in [("price", "indexed"), ("supply", "indexed"), ("price", "full_csv"),
                 ("supply", "full_csv"), ("region", "full_csv")]:
        assert pair in actual, (pair, actual)
    assert ("region", "indexed") not in actual
    assert "24" in response and "sparse" in response.lower(), response
    result = {"status": "passed", "entry_exit": "orchestrator",
              "engine": "@fast.orchestrator" if engine == "native" else "@fast.agent(agents=[...])",
              "underlying_engine": "IterativePlanner" if engine == "native" else "AgentsAsToolsAgent",
              "elapsed_seconds": time.monotonic() - start,
              "synthetic_fixture": True, "injected_control": "index_omission", "headline_eligible": False,
              "query_sha256": tools.query_hash, "plans": tools.plans, "reviews": tools.reviews,
              "actual_tool_routes": actual, "report": tools.report}
    write_json(evidence.directory / "native-result.json", result)
    return result


async def run(args: argparse.Namespace, evidence: Evidence) -> dict:
    os.environ["FAST_AGENT_HOME"] = str(ROOT / "configs/fast-agent-home")
    sources = ["scripts/probe_fast_agent.py", "scripts/probe_tools.py", "scripts/probe_support.py",
               "scripts/probe_tool_playback.py", "configs/fast-agent.yaml", "configs/model_manifest.json"]
    hashes = {}
    for source in sources:
        data = (ROOT / source).read_bytes()
        hashes[source] = hashlib.sha256(data).hexdigest()
        target = evidence.directory / "sources" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    write_json(evidence.directory / "source-hashes.json", hashes)
    write_json(evidence.directory / "environment.json", {
        "python": platform.python_version(), "fast_agent": version("fast-agent-mcp"),
        "constructor": str(inspect.signature(FastAgent)),
        "orchestrator": str(inspect.signature(FastAgent.orchestrator)),
        "request_params_fields": sorted(RequestParams.model_fields)})
    if args.stage == "replay":
        if not args.capture:
            raise ValueError("--capture required for replay")
        return await replay_decisions(evidence, ROOT / "configs/fast-agent.yaml", args.capture.resolve())
    with RecordingProxy(evidence) as proxy:
        config = evidence.directory / "fast-agent.yaml"
        config.write_text((ROOT / "configs/fast-agent.yaml").read_text().replace(
            "http://127.0.0.1:11434/v1", proxy.base_url))
        result = {}
        if args.stage in ("all", "decision"):
            keys = await capture_decisions(evidence, config, proxy)
            write_json(evidence.directory / "decision-index.json", {"cassette_keys": keys})
            result["decisions"] = {"status": "passed", "seeds": list(SEEDS), "cassette_keys": keys}
        if args.stage in ("all", "native"):
            result["native"] = await native_orchestration(evidence, config)
        if args.stage == "agents-tools":
            result["agents_as_tools"] = await native_orchestration(evidence, config, engine="agents-tools")
        return {**result, "provider_requests": len(proxy.requests), "status": "passed"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["all", "decision", "native", "agents-tools", "replay"], default="all")
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    name = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + args.stage + "-" + uuid.uuid4().hex[:6]
    evidence = Evidence(ROOT / "artifacts/framework_probe" / name)
    print(f"Probe evidence: {evidence.directory.relative_to(ROOT)}", flush=True)
    started = time.monotonic()
    try:
        result = asyncio.run(run(args, evidence))
        result["elapsed_seconds_total"] = time.monotonic() - started
        write_json(evidence.directory / "result.json", result)
        print(canonical(result), flush=True)
        return 0
    except BaseException as error:
        write_json(evidence.directory / "result.json", {"status": "failed", "error": repr(error),
                   "traceback": traceback.format_exc(), "elapsed_seconds_total": time.monotonic() - started})
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
