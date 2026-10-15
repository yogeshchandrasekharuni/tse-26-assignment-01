"""Final file/lineage/resource audit after the actual submission target succeeds."""

import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from housing.evaluation.aggregate import case_semantics
from housing.evaluation.models import CaseResult, LegOutcome
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.reporting.campaign_observability import verify_campaign_observability
from housing.reporting.plan_observability import verify_plan_observability

packet = Path(__file__).resolve().parent
command = json.loads((packet / "submission-command.json").read_bytes())
assert command["exit_code"] == 0
assert command["log_sha256"] == sha256_bytes((packet / "submission-check.log").read_bytes())
clean_path = ROOT / "reports/data/clean-checkout.json"
clean = json.loads(clean_path.read_bytes())
assert clean["status"] == "verified" and clean["scope"] == "headline"
assert clean["logical_comparisons"] == 900 and clean["initial_git_status"] == ""
assert clean["revision"] == "8eb6727d7236f7bce14c97fdf9f5f86fddea1121"
assert all(step["exit_code"] == 0 for step in clean["commands"])
code_changes = subprocess.check_output(
    [
        "git",
        "diff",
        "--name-only",
        clean["revision"],
        "--",
        "src",
        "scripts",
        "tests",
        "configs",
        "prompts",
        "uv.lock",
        "pyproject.toml",
        "Makefile",
    ],
    cwd=ROOT,
    text=True,
)
assert not code_changes.strip(), code_changes
assert len(clean["reproductions"]) == 1
replay = ROOT / clean["reproductions"][0]
hashes = json.loads((replay / "artifact_hashes.json").read_bytes())
observed = {
    str(path.relative_to(replay)): sha256_bytes(path.read_bytes())
    for path in replay.rglob("*")
    if path.is_file() and path.name != "artifact_hashes.json"
}
assert observed == hashes
cases = [
    CaseResult.model_validate_json(p.read_bytes()) for p in sorted((replay / "cases").glob("*/result.json"))
]
assert len(cases) == 900
for case in cases:
    original = CaseResult.model_validate_json(
        (
            ROOT
            / "artifacts/campaigns/headline-live-v1/cases"
            / f"{case.mr_id}-{case.base_id}-s{case.seed}"
            / "result.json"
        ).read_bytes()
    )
    assert semantic_hash(case_semantics(case)) == semantic_hash(case_semantics(original))
processes: Counter[int] = Counter()
decisions = failed_attributions = physical = 0
for record in replay.glob("cases/*/attempt-*/*/record.json"):
    physical += 1
    outcome = LegOutcome.model_validate_json(record.read_bytes())
    run = ROOT / outcome.run_path
    terminal = json.loads((run / "terminal.json").read_bytes())
    assert terminal["network_attempts"] == [] and not terminal["cassette_hashes"]
    assert terminal["model_decisions"] == len(list((run / "model").glob("*.response.json")))
    decisions += terminal["model_decisions"]
    execution = json.loads((record.parent / "execution-process.json").read_bytes())
    assert execution["revision"] == "bounded-process-playback-2"
    assert execution["source_sha256"] == sha256_bytes(
        (ROOT / "src/housing/reporting/isolated_replay.py").read_bytes()
    )
    processes[execution["worker_pid"]] += 1
    if outcome.status == "failed":
        failed_attributions += 1
        before_path = record.parent / "record.before-seed-attribution.json"
        before = LegOutcome.model_validate_json(before_path.read_bytes())
        attribution = json.loads((record.parent / "seed-attribution.json").read_bytes())
        assert before.effective_seed is None and outcome.effective_seed == outcome.requested_seed
        assert before.model_dump(exclude={"effective_seed"}) == outcome.model_dump(exclude={"effective_seed"})
        assert attribution["original_leg_record_sha256"] == sha256_bytes(before_path.read_bytes())
        assert attribution["replay_terminal_sha256"] == sha256_bytes((run / "terminal.json").read_bytes())
assert physical == 1194 and failed_attributions == 272 and decisions == 10753
assert max(processes.values()) <= 16
assert sum(case.status == "pass" for case in cases) == 690
assert sum(case.status == "violation" and case.violation_kind == "output_contract" for case in cases) == 210
dashboard = verify_campaign_observability()
plan = verify_plan_observability()
pdf = ROOT / "output/pdf/housing-report.pdf"
qa_path = ROOT / "reports/data/pdf-qa.json"
qa = json.loads(qa_path.read_bytes())
assert qa["status"] == "verified" and qa["inspected_pages"] == list(range(1, 13))
assert qa["pdf_sha256"] == sha256_bytes(pdf.read_bytes())
write_json(
    packet / "audit.json",
    {
        "status": "verified_current_deliverable_files",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "tested_revision": clean["revision"],
        "logical_comparisons": len(cases),
        "physical_replay_analyses": physical,
        "replayed_decisions": decisions,
        "fresh_model_calls": 0,
        "historical_failed_seed_attributions": failed_attributions,
        "analysis_processes_observed": len(processes),
        "maximum_analyses_per_process_observed": max(processes.values()),
        "dashboard_proof_inputs": len(dashboard),
        "current_plan_browser_proof_inputs": len(plan),
        "reproduction_artifacts_verified": len(hashes),
        "clean_checkout_sha256": sha256_bytes(clean_path.read_bytes()),
        "pdf_sha256": sha256_bytes(pdf.read_bytes()),
        "pdf_qa_sha256": sha256_bytes(qa_path.read_bytes()),
        "submission_command_sha256": sha256_bytes((packet / "submission-command.json").read_bytes()),
        "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "interpretation": "Current files and actual command evidence verified. Final Git inventory and any source ZIP are checked separately before goal completion.",
    },
)
print(
    f"Final audit verified900 comparisons/{physical} actual offline analyses/{decisions} decisions, zero network, bounded process lifetimes and12 inspected PDF pages."
)
