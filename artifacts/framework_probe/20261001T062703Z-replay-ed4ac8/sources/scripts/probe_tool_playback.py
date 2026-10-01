"""Check captured native tool calls execute during Fast Agent playback, with strict input guards."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fast_agent import Prompt, load_prompt
from fast_agent.agents.tool_runner import ToolRunnerHooks
from fast_agent.mcp.prompt_serialization import save_messages

from probe_fast_agent import ROOT, fast_instance, model_identity, register
from probe_support import Evidence, RecordingProxy, deny_network, digest, write_json
from probe_tools import ProbeTools

INSTRUCTION = "PROBE_ROLE=price. Call scan_price exactly once, then return its receipt as JSON."
PROMPT = "Execute the real price scan for the controller-bound synthetic probe fixture."


def boundary() -> dict:
    return {"instruction": INSTRUCTION, "prompt": PROMPT, "model": model_identity(104729),
            "tool_schema_version": "framework-spike-1", "semantic_projection": "framework-spike-1",
            "tool_bundle_sha256": hashlib.sha256((ROOT / "scripts/probe_tools.py").read_bytes()).hexdigest(),
            "dependency_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
            "framework_config_sha256": hashlib.sha256((ROOT / "configs/fast-agent.yaml").read_bytes()).hexdigest(),
            "overlay_sha256": hashlib.sha256((ROOT / "configs/fast-agent-home/model-overlays/housing-s104729.yaml").read_bytes()).hexdigest()}


def semantic_messages(messages: list[dict]) -> list[dict]:
    """Remove only framework audit metadata, which the provider converter does not prompt.
    Keep all text, native tool calls/results, reasoning channels and control fields exact."""
    excluded_channels = {"fast-agent-timing", "fast-agent-usage", "fast-agent-tool-timing"}
    result = []
    for original in messages:
        message = {key: value for key, value in original.items() if key != "timestamp"}
        if "channels" in message:
            channels = {k: v for k, v in message["channels"].items() if k not in excluded_channels}
            if channels:
                message["channels"] = channels
            else:
                del message["channels"]
        result.append(message)
    return result


async def capture(evidence: Evidence, config: Path) -> None:
    tools = ProbeTools(evidence)

    def scan_price() -> dict:
        """Run the exact controller-bound fixture price scan and return a receipt."""
        return tools.scan_price()

    inputs: list[str] = []
    responses = []

    async def before(runner, messages):
        payload = [m.model_dump(mode="json", exclude_none=True) for m in messages]
        write_json(evidence.directory / f"capture-input-{len(inputs)}.json", payload)
        inputs.append(digest(semantic_messages(payload)))

    async def after(runner, message):
        responses.append(message.model_copy(deep=True))

    fast = fast_instance(config)
    register(fast, "price", INSTRUCTION, "housing-s104729", [scan_price])
    async with fast.run() as agents:
        agents.price.tool_runner_hooks = ToolRunnerHooks(before_llm_call=before, after_llm_call=after)
        final = await agents.price.send(PROMPT)
    assert len(responses) == 2 and responses[0].tool_calls, "Expected one real tool call plus final response"
    save_messages([Prompt.user(PROMPT), *responses], str(evidence.directory / "native-conversation.json"))
    write_json(evidence.directory / "native-capture.json", {
        "origin": "live_captured", "boundary": boundary(), "input_hashes": inputs,
        "final_response": final, "expected_receipt": tools.receipts["price"]})


async def replay(evidence: Evidence, capture_dir: Path, *, mutate: bool) -> dict:
    record = json.loads((capture_dir / "native-capture.json").read_text())
    assert record["origin"] == "live_captured" and record["boundary"] == boundary()
    tools = ProbeTools(evidence)

    def scan_price() -> dict:
        """Run the exact controller-bound fixture price scan and return a receipt."""
        result = tools.scan_price()
        if mutate:
            result = {**result, "selected_observations": result["selected_observations"] + 1}
        return result

    checked = 0

    async def before(runner, messages):
        nonlocal checked
        payload = [m.model_dump(mode="json", exclude_none=True) for m in messages]
        write_json(evidence.directory / f"replay-input-{mutate}-{checked}.json", payload)
        actual = digest(semantic_messages(payload))
        if checked >= len(record["input_hashes"]) or actual != record["input_hashes"][checked]:
            evidence.log("REPLAY_MISS", stage="before_next_model_response", changed_tool_control=mutate)
            raise ValueError("REPLAY_MISS: upstream native tool result differs")
        checked += 1

    fast = fast_instance(ROOT / "configs/fast-agent.yaml")
    register(fast, "price", INSTRUCTION, "playback", [scan_price])
    with deny_network() as network_attempts:
        async with fast.run() as agents:
            loaded = await agents.price.generate(load_prompt(capture_dir / "native-conversation.json"))
            assert loaded.first_text().startswith("HISTORY LOADED")
            agents.price.tool_runner_hooks = ToolRunnerHooks(before_llm_call=before)
            try:
                final = await agents.price.send(PROMPT)
            except ValueError as error:
                if not mutate or "REPLAY_MISS" not in str(error):
                    raise
                assert checked == 1 and "price" in tools.receipts
                assert not network_attempts
                return {"status": "passed", "changed_upstream_result_rejected": True,
                        "model_decisions_consumed": checked, "tools_executed": 1}
            assert not mutate, "Changed tool result was silently replayed"
            assert final == record["final_response"]
            assert checked == 2 and tools.receipts["price"] == record["expected_receipt"]
        assert not network_attempts
    return {"status": "passed", "native_tool_call_replayed": True, "tools_reexecuted": 1,
            "model_decisions_consumed": checked, "network_attempts": 0}


async def run(evidence: Evidence, capture_dir: Path | None) -> dict:
    os.environ["FAST_AGENT_HOME"] = str(ROOT / "configs/fast-agent-home")
    if capture_dir is None:
        with RecordingProxy(evidence) as proxy:
            config = evidence.directory / "fast-agent.yaml"
            config.write_text((ROOT / "configs/fast-agent.yaml").read_text().replace(
                "http://127.0.0.1:11434/v1", proxy.base_url))
            await capture(evidence, config)
        capture_dir = evidence.directory
    valid = await replay(evidence, capture_dir, mutate=False)
    changed = await replay(evidence, capture_dir, mutate=True)
    return {"status": "passed", "capture": str(capture_dir.relative_to(ROOT)),
            "offline_native_playback": valid, "injected_replay_guard_control": changed,
            "headline_eligible": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-tool-playback-" + uuid.uuid4().hex[:6]
    evidence = Evidence(ROOT / "artifacts/framework_probe" / label)
    print(f"Probe evidence: {evidence.directory.relative_to(ROOT)}", flush=True)
    try:
        result = asyncio.run(run(evidence, args.capture.resolve() if args.capture else None))
    except BaseException as error:
        write_json(evidence.directory / "result.json", {"status": "failed", "error": repr(error),
                                                      "traceback": traceback.format_exc()})
        traceback.print_exc()
        return 1
    write_json(evidence.directory / "result.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
