"""Preserve the predetermined first twenty MR05 bases; no full-relation or rate claim."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.evaluation.models import CaseResult, Cohort
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import project_capture
from housing.replay.capture import load_cassettes

proof = Path(__file__).resolve().parent
campaign = ROOT / "artifacts/campaigns/headline-live-v1"
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
selected_bases = {f"b{number:03}" for number in range(1, 21)}
specs = {spec.base_id: spec for spec in cohort.cases if spec.mr == "MR05" and spec.base_id in selected_bases}
assert len(specs) == 20 and all(spec.eligibility.eligible for spec in specs.values())
assert len({spec.base_query_sha256 for spec in specs.values()}) == 20
assert cohort.seeds == (104729, 130363, 155921)
paths = [campaign / "cases" / f"MR05-{base}-s{seed}" / "result.json"
         for base in sorted(specs) for seed in cohort.seeds]
assert len(paths) == 60 and all(path.is_file() for path in paths), "Wait for all first-twenty-base seed panels"
seen = set()
directories = set()
case_paths = []
failures = []
hashes = {}
attempts = 0
source_reuses = []
for path in paths:
    case = CaseResult.model_validate_json(path.read_bytes())
    assert case.mr_id == "MR05" and case.mode == "live"
    assert case.campaign_id == case.live_campaign_id == campaign.name
    assert case.status in {"pass", "violation"}
    assert case.cohort_case_sha256 == semantic_hash(specs[case.base_id])
    key = (case.base_id, case.seed)
    assert key not in seen
    seen.add(key)
    case_paths.append(str(path.parent.relative_to(ROOT)))
    attempts += len(list(path.parent.glob("attempt-*/case.json")))
    for item in path.parent.rglob("*"):
        if item.is_file():
            hashes[str(item.relative_to(ROOT))] = sha256_bytes(item.read_bytes())
    if case.source_reused_from is not None:
        reused_record = (ROOT / case.source_reused_from).resolve()
        assert reused_record.is_relative_to(campaign)
        record = json.loads(reused_record.read_bytes())
        assert record.get("source", record) == case.source.model_dump(mode="json")
        digest = sha256_bytes(reused_record.read_bytes())
        hashes[str(reused_record.relative_to(ROOT))] = digest
        source_reuses.append({"case": path.parent.name, "record": case.source_reused_from,
                              "record_sha256": digest, "source_run_path": case.source.run_path})
    for name in ("source", "followup"):
        leg = getattr(case, name)
        assert leg.requested_seed == leg.effective_seed == case.seed
        directory = (ROOT / leg.run_path).resolve()
        assert directory.is_relative_to(campaign)
        request = AnalysisRequest.model_validate_json((directory / "request.json").read_bytes())
        expected = getattr(specs[case.base_id], name + "_request").model_copy(update={"seed": case.seed})
        assert request == expected and semantic_hash(request) == leg.request_sha256
        assert leg.view_sha256 == getattr(specs[case.base_id], name + "_view_sha256")
        terminal = json.loads((directory / "terminal.json").read_bytes())
        assert terminal["status"] == leg.status
        if leg.status == "completed":
            output = AnalysisOutput.model_validate_json((directory / "output.json").read_bytes())
            assert semantic_hash(output) == leg.output_sha256
            assert semantic_hash(output.canonical) == leg.canonical_sha256 == terminal["canonical_sha256"]
        else:
            assert terminal["code"] == leg.error_code and terminal["stage"] == leg.error_stage
            failures.append({"case": path.parent.name, "leg": name, "code": leg.error_code,
                             "stage": leg.error_stage, "run_path": leg.run_path})
        directories.add(directory)
assert seen == {(base, seed) for base in specs for seed in cohort.seeds}

runs = []
for directory in sorted(directories):
    for item in directory.rglob("*"):
        if item.is_file():
            hashes[str(item.relative_to(ROOT))] = sha256_bytes(item.read_bytes())
    cassettes = load_cassettes(directory)
    terminal = json.loads((directory / "terminal.json").read_bytes())
    expected_hashes = terminal["cassette_hashes"]
    files = sorted((directory / "cassettes").glob("*.json"))
    assert set(expected_hashes) == {path.stem for path in files}
    assert all(sha256_bytes(path.read_bytes()) == expected_hashes[path.stem] for path in files)
    assert len(cassettes) == terminal["model_decisions"]
    projection = project_capture(directory)
    runs.append({"run_path": str(directory.relative_to(ROOT)), "cassettes": len(cassettes),
                 "owned_by_MR05": directory.relative_to(campaign / "cases").parts[0].startswith("MR05-"),
                 "offline_projection_observations": len(projection.spans)})

frozen = ["src/housing/contracts", "src/housing/data", "src/housing/tools", "src/housing/agents",
          "src/housing/workflow", "src/housing/replay", "src/housing/evaluation", "src/housing/identity.py",
          "pyproject.toml", "uv.lock", "prompts/v3", "configs", "EVALUATION_NOTES.md",
          "data/frozen", "data/manifests"]
changed = subprocess.check_output(["git", "diff", "--name-only", "8a50f75", "--", *frozen],
                                  cwd=ROOT, text=True).strip()
assert not changed, changed
hash_path = proof / "partial-artifact-hashes.json"
hash_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
packet = {
    "status": "verified_partial_relation_checkpoint", "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Predetermined MR05 bases b001-b020, all three fixed seeds. Partial preservation only: no complete thirty-base relation, final rates, full-campaign completion, replay or dashboard-delivery claim.",
    "campaign_id": campaign.name, "mr_id": "MR05", "eligible_distinct_bases": 20,
    "resolved_comparisons": 60, "fixed_seeds": list(cohort.seeds),
    "resolved_infrastructure_errors": 0, "preserved_case_attempts": attempts,
    "case_paths": case_paths, "referenced_physical_captures": runs, "failed_legs": failures,
    "new_physical_captures_owned_by_MR05": sum(run["owned_by_MR05"] for run in runs),
    "reused_source_legs": source_reuses,
    "verified_cassettes": sum(run["cassettes"] for run in runs),
    "artifact_files": len(hashes), "artifact_index_sha256": sha256_bytes(hash_path.read_bytes()),
    "cohort_sha256": sha256_bytes(cohort_path.read_bytes()), "frozen_diff_from_8a50f75": [],
    "live_progress_at_check": json.loads((campaign / "progress.json").read_bytes()),
}
(proof / "partial-checkpoint.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"referenced_physical_captures", "case_paths", "failed_legs", "reused_source_legs"}}, indent=2))
