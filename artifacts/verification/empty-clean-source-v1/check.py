"""Executed auxiliary proof: fresh committed source, existing locked interpreter/packages."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from housing.api.app import create_app
from housing.api.registry import CAPTURES
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.replay.network import deny_network
from housing.workflow.service import run_analysis

parser = argparse.ArgumentParser()
parser.add_argument("--expected-root", type=Path, required=True)
args = parser.parse_args()
assert ROOT == args.expected_root.resolve()
assert not (ROOT / "observability/langfuse/.env").exists()
assert not (ROOT / "artifacts/runtime/web").exists()
binding = CAPTURES["empty"]
before = {str(p.relative_to(binding.directory)): sha256_bytes(p.read_bytes())
          for p in binding.directory.rglob("*") if p.is_file()}

with TestClient(create_app(ROOT / "artifacts/empty-clean-api")) as client:
    with deny_network() as api_network_attempts:
        response = client.get("/api/analyses/capture/empty")
        assert response.status_code == 200
        view = response.json()
        assert view["output"]["canonical"]["summary"]["total_observations"] == 0
        assert len(view["months"]) == 12
        assert view["price_ticks"] == view["ppsf_ticks"] == []
        response = client.get("/api/analyses/capture/empty/workflow")
        assert response.status_code == 200
        workflow = response.json()
        assert workflow["model_decisions"] == 16
        assert workflow["refinements"] == 1 and workflow["query_unchanged"]
        trace = client.get("/api/analyses/capture/empty/trace")
        assert trace.status_code == 200
        assert trace.content == (binding.directory / "trace.jsonl").read_bytes()
        for sequence in (0, 15):
            turn = client.get(f"/api/analyses/capture/empty/model/{sequence}")
            assert turn.status_code == 200
            assert turn.json()["input"] is not None and turn.json()["response"] is not None
        assert api_network_attempts == []

output = asyncio.run(run_analysis(
    binding.request(), binding.snapshot(), mode="replay", capture=binding.directory,
    artifact_root=ROOT / "artifacts/empty-clean-replay",
))
directory = ROOT / "artifacts/empty-clean-replay" / output.metadata.run_id
terminal = json.loads((directory / "terminal.json").read_bytes())
expected = json.loads((binding.directory / "terminal.json").read_bytes())
assert terminal["status"] == "completed"
assert terminal["model_decisions"] == expected["model_decisions"] == 16
assert terminal["network_attempts"] == []
assert semantic_hash(output.canonical) == expected["canonical_sha256"]
after = {str(p.relative_to(binding.directory)): sha256_bytes(p.read_bytes())
         for p in binding.directory.rglob("*") if p.is_file()}
assert before == after
packet = {
    "status": "verified", "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Auxiliary clean-source empty-capture API/playback proof; reuses locked packages, not fresh setup or full headline reproduction.",
    "root": str(ROOT), "original_runtime_absent": True, "credentials_absent": True,
    "api_network_attempts": api_network_attempts,
    "trace_sha256": sha256_bytes(trace.content), "capture_files_unchanged": len(before),
    "workflow_refinements": 1, "model_turns_read": [0, 15],
    "replay_path": str(directory.relative_to(ROOT)), "terminal": terminal,
}
(ROOT / "artifacts/empty-clean-result.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps(packet, indent=2))
