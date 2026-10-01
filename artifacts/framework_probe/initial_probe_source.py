"""Installed-API proof, not an authored decision fixture."""
import asyncio
import inspect
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

from fast_agent import FastAgent, load_prompt
from fast_agent.types import RequestParams

OUT = Path("artifacts/framework_probe")


async def main():
    evidence = {"python": platform.python_version(), "fast_agent": version("fast-agent-mcp"),
                "constructor": str(inspect.signature(FastAgent)),
                "agent": str(inspect.signature(FastAgent.agent)), "calls": []}
    fast = FastAgent("housing-probe", config_path="configs/fast-agent.yaml", parse_cli_args=False,
                     quiet=True, no_home=True)
    for name in ["orchestrator", "reviewer"]:
        async def register():
            pass
        fast.agent(name=name, instruction="Return only valid JSON. No prose. /no_think",
                   model="generic.housing-qwen-s104729", use_history=False, skills=[],
                   request_params=RequestParams(max_tokens=1024, use_history=False))(register)
    start = time.monotonic()
    async with fast.run() as agents:
        prompt = 'Return a JSON object with role="orchestrator" and action="INITIAL". /no_think'
        response = await agents.orchestrator.send(prompt)
        evidence["calls"].append({"role": "orchestrator", "prompt": prompt, "response": response})
        json.loads(response)
        response2 = await agents.reviewer.send('Return {"role":"reviewer","decision":"ACCEPT"}. /no_think')
        json.loads(response2)
        evidence["calls"].append({"role": "reviewer", "response": response2})
    evidence["live_seconds"] = time.monotonic() - start
    conversation = OUT / "conversation.txt"
    conversation.write_text(f"---USER\n{prompt}\n---ASSISTANT\n{response}\n")
    playback = FastAgent("housing-playback-probe", config_path="configs/fast-agent.yaml",
                         parse_cli_args=False, quiet=True, no_home=True)
    @playback.agent(name="recorded", instruction="Replay", model="playback", skills=[], use_history=False)
    async def recorded():
        pass
    async with playback.run() as agents:
        loaded = await agents.recorded.generate(load_prompt(conversation))
        assert loaded.first_text().startswith("HISTORY LOADED")
        replayed = await agents.recorded.send(prompt)
        assert replayed == response, (replayed, response)
        evidence["playback_equal"] = True
    evidence["status"] = "passed"
    (OUT / "probe.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
