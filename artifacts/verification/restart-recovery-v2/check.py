"""Read-only integrity audit before resuming the reboot-interrupted live campaign."""

import json
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.evaluation.models import CaseResult, Cohort
from housing.evaluation.transforms import updated_request
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.replay.capture import load_cassettes
from housing.workflow.boundary import RunManifest

packet = Path(__file__).resolve().parent
campaign = ROOT / "artifacts/campaigns/headline-live-v1"
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
manifest = json.loads((campaign / "manifest.json").read_bytes())
assert sha256_bytes(cohort_path.read_bytes()) == manifest["cohort_sha256"]
specs = {(spec.mr, spec.base_id): spec for spec in cohort.cases}
hashes = {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in sorted(campaign.rglob("*")) if path.is_file()}
current_inputs: dict[str, str] = {}
runs: set[Path] = set()
counts: Counter[str] = Counter()
statuses: Counter[str] = Counter()
keys = set()
results = sorted((campaign / "cases").glob("*/result.json"))
assert len(results) == 743
for path in results:
    case = CaseResult.model_validate_json(path.read_bytes())
    spec = specs[(case.mr_id, case.base_id)]
    assert case.campaign_id == case.live_campaign_id == campaign.name and case.mode == "live"
    assert case.cohort_case_sha256 == semantic_hash(spec)
    assert case.seed in cohort.seeds
    key = (case.mr_id, case.base_id, case.seed)
    assert key not in keys
    keys.add(key)
    counts[case.mr_id] += 1
    statuses[case.status] += 1
    if case.source_reused_from:
        reused = (ROOT / case.source_reused_from).resolve()
        assert reused.is_relative_to(campaign)
        record = json.loads(reused.read_bytes())
        assert record.get("source", record) == case.source.model_dump(mode="json")
    for label, leg in (("source", case.source), ("followup", case.followup)):
        run = (ROOT / leg.run_path).resolve()
        assert run.is_relative_to(campaign)
        request = AnalysisRequest.model_validate_json((run / "request.json").read_bytes())
        assert request == updated_request(getattr(spec, label + "_request"), seed=case.seed)
        assert semantic_hash(request) == leg.request_sha256
        assert leg.view_sha256 == getattr(spec, label + "_view_sha256")
        terminal = json.loads((run / "terminal.json").read_bytes())
        assert terminal["status"] == leg.status
        if leg.status == "completed":
            output = AnalysisOutput.model_validate_json((run / "output.json").read_bytes())
            assert semantic_hash(output) == leg.output_sha256
            assert semantic_hash(output.canonical) == leg.canonical_sha256 == terminal["canonical_sha256"]
        else:
            assert terminal["code"] == leg.error_code and terminal["stage"] == leg.error_stage
        if run in runs:
            continue
        runs.add(run)
        boundary = RunManifest.model_validate_json((run / "run-manifest.json").read_bytes())
        assert boundary.mode == "live"
        assert semantic_hash(boundary.identity) == boundary.boundary_sha256 == leg.execution_key
        assert boundary.identity.fast_agent_version == version("fast-agent-mcp")
        assert boundary.identity.pydantic_version == version("pydantic")
        for name, digest in boundary.identity.inputs.items():
            if name not in current_inputs:
                current_inputs[name] = sha256_bytes((ROOT / name).read_bytes())
            assert current_inputs[name] == digest, name
        cassettes = load_cassettes(run) if terminal["model_decisions"] else ()
        assert len(cassettes) == terminal["model_decisions"]
        expected = terminal["cassette_hashes"]
        files = sorted((run / "cassettes").glob("*.json"))
        assert set(expected) == {p.stem for p in files}
        for f in files:
            assert hashes[str(f.relative_to(ROOT))] == expected[f.stem]
expected_order = [(spec.mr, spec.base_id, seed) for spec in cohort.cases for seed in cohort.seeds]
assert keys == set(expected_order[:743])
old_indexes = []
for index in sorted((ROOT / "artifacts/verification").glob("mr0*-live-checkpoint-v1/*artifact-hashes.json")):
    old = json.loads(index.read_bytes())
    for name, digest in old.items():
        assert hashes[name] == digest, name
    old_indexes.append({"path": str(index.relative_to(ROOT)), "files": len(old)})
interrupted = campaign / "cases/MR09-b008-s155921/attempt-001/followup/runs/20261011T202737Z-3f4778873a"
assert not (interrupted / "terminal.json").exists()
partial_cassettes = load_cassettes(interrupted)
assert len(partial_cassettes) == 6
partial_inputs = sorted((interrupted / "model").glob("*.input.json"))
assert len(partial_inputs) == 7
for f in partial_inputs:
    json.loads(f.read_bytes())
index_path = packet / "pre-resume-artifact-hashes.json"
write_json(index_path, hashes)
write_json(packet / "audit.json", {
    "status": "verified_completed_evidence_before_resume",
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "completed_comparisons": len(results),
    "completed_by_mr": dict(sorted(counts.items())),
    "physical_terminal_captures_verified": len(runs),
    "frozen_inputs_verified": len(current_inputs),
    "previous_indexes_reverified": old_indexes,
    "artifact_files": len(hashes),
    "artifact_index_sha256": sha256_bytes(index_path.read_bytes()),
    "interrupted_run": str(interrupted.relative_to(ROOT)),
    "interrupted_recorded_model_responses": len(partial_cassettes),
    "interrupted_recorded_model_inputs": len(partial_inputs),
    "interrupted_terminal_present": False,
    "lost_temporary_console": "/private/tmp/housing-headline-live-v1.log",
    "scope": "Integrity and retained interruption only; not full campaign completion or replay",
})
print(f"Verified {len(results)} completed comparisons, {len(runs)} terminal captures, {len(hashes)} raw files and {len(current_inputs)} frozen inputs. Retained incomplete run has six captured decisions and a seventh input without a response.")
