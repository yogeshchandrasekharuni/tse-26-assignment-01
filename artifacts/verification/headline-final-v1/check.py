"""Read-only full-corpus audit; keeps numeric and output-contract denominators explicit."""

import json
from collections import Counter
from datetime import UTC, datetime
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path

from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.evaluation.models import CaseResult, Cohort, HeadlineRow
from housing.evaluation.transforms import updated_request
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.replay.capture import load_cassettes
from housing.reporting.interruptions import validated_interruption
from housing.workflow.boundary import RunManifest


def rate24(x: int, n: int) -> str:
    """Exact integer half-even formatting for the declared 24-place headline rate."""
    value = Fraction(x, n)
    scale = 10**24
    rounded, remainder = divmod(value.numerator * scale, value.denominator)
    doubled = 2 * remainder
    if doubled > value.denominator or (doubled == value.denominator and rounded % 2):
        rounded += 1
    return f"{rounded // scale}.{rounded % scale:024d}"


def main() -> None:
    packet = Path(__file__).resolve().parent
    campaign = ROOT / "artifacts/campaigns/headline-live-v1"
    required = ("finished.json", "headline.json", "cases.jsonl", "runtime.json", "artifact_hashes.json")
    if not all((campaign / name).is_file() for name in required):
        raise ValueError("Full live campaign closure is required; partial outcomes are not final evidence")
    manifest = json.loads((campaign / "manifest.json").read_bytes())
    cohort_path = ROOT / "configs/headline-cohort-v1.json"
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    assert manifest["mode"] == "live" and manifest["expected_comparisons"] == 900
    assert sha256_bytes(cohort_path.read_bytes()) == manifest["cohort_sha256"]
    assert cohort.seeds == (104729, 130363, 155921) and len(cohort.cases) == 300
    specs = {(spec.mr, spec.base_id): spec for spec in cohort.cases}
    expected = {(spec.mr, spec.base_id, seed) for spec in cohort.cases for seed in cohort.seeds}
    stored_hashes = json.loads((campaign / "artifact_hashes.json").read_bytes())
    for relative, digest in stored_hashes.items():
        path = (campaign / relative).resolve()
        assert path.is_relative_to(campaign) and sha256_bytes(path.read_bytes()) == digest, relative
    cases = [
        CaseResult.model_validate_json(line) for line in (campaign / "cases.jsonl").read_text().splitlines()
    ]
    assert len(cases) == 900
    assert {(case.mr_id, case.base_id, case.seed) for case in cases} == expected
    physical_references: set[str] = set()
    reused_sources = 0
    for case in cases:
        spec = specs[(case.mr_id, case.base_id)]
        assert case.mode == "live" and case.campaign_id == case.live_campaign_id == campaign.name
        assert case.status != "execution_error"
        assert case.cohort_case_sha256 == semantic_hash(spec)
        assert case.base_semantic_sha256 == spec.base_query_sha256
        assert case.transform_sha256 == semantic_hash(spec.recipe)
        latest = campaign / "cases" / f"{case.mr_id}-{case.base_id}-s{case.seed}" / "result.json"
        assert CaseResult.model_validate_json(latest.read_bytes()) == case
        if case.source_reused_from:
            reused_sources += 1
            reused = (ROOT / case.source_reused_from).resolve()
            assert reused.is_relative_to(campaign)
            record = json.loads(reused.read_bytes())
            assert record.get("source", record) == case.source.model_dump(mode="json")
            assert case.source.status == "completed"
        for label, leg in (("source", case.source), ("followup", case.followup)):
            run = (ROOT / leg.run_path).resolve()
            assert run.is_relative_to(campaign)
            physical_references.add(leg.run_path)
            request = AnalysisRequest.model_validate_json((run / "request.json").read_bytes())
            assert request == updated_request(getattr(spec, label + "_request"), seed=case.seed)
            assert semantic_hash(request) == leg.request_sha256
            assert leg.view_sha256 == getattr(spec, label + "_view_sha256")
            assert leg.requested_seed == case.seed
            terminal = json.loads((run / "terminal.json").read_bytes())
            assert terminal["status"] == leg.status
            if leg.status == "completed":
                assert leg.effective_seed == case.seed
                output = AnalysisOutput.model_validate_json((run / "output.json").read_bytes())
                assert semantic_hash(output) == leg.output_sha256
                assert semantic_hash(output.canonical) == leg.canonical_sha256 == terminal["canonical_sha256"]
            else:
                assert terminal["code"] == leg.error_code and terminal["stage"] == leg.error_stage

    rows = [HeadlineRow.model_validate(row) for row in json.loads((campaign / "headline.json").read_bytes())]
    assert len(rows) == 10 and {row.mr_id for row in rows} == {spec.mr for spec in cohort.cases}
    independent_counts = []
    for row in rows:
        group = [case for case in cases if case.mr_id == row.mr_id]
        bases = {case.base_id for case in group}
        violating = {case.base_id for case in group if case.status == "violation"}
        counts = Counter(case.status for case in group)
        kinds = Counter(case.violation_kind for case in group if case.status == "violation")
        numeric = [case for case in group if case.comparison is not None]
        assert len(group) == 90 and len(bases) == 30 and row.complete
        assert len({case.base_semantic_sha256 for case in group}) == 30
        assert all({c.seed for c in group if c.base_id == base} == set(cohort.seeds) for base in bases)
        assert row.completed_bases == 30 and row.violating_bases == len(violating)
        assert row.base_rate == rate24(len(violating), 30)
        assert row.seed_pairs_completed == 90 and row.seed_pair_violations == counts["violation"]
        assert row.output_contract_violations == kinds["output_contract"]
        assert len(numeric) + kinds["output_contract"] == 90
        assert row.execution_errors == row.invalid_candidates == 0
        independent_counts.append(
            {
                "mr_id": row.mr_id,
                "completed_bases": len(bases),
                "violating_bases": len(violating),
                "paired_outcomes": dict(sorted(counts.items())),
                "output_contract_pairs": kinds["output_contract"],
                "numeric_pairs_with_both_outputs": len(numeric),
                "numeric_relation_violations": kinds["relation"],
                "paired_outcomes_by_seed": {
                    str(seed): dict(sorted(Counter(c.status for c in group if c.seed == seed).items()))
                    for seed in cohort.seeds
                },
            }
        )

    frozen_inputs: dict[str, str] = {}
    terminal_counts: Counter[str] = Counter()
    physical_failure_codes: Counter[str] = Counter()
    interruptions = []
    cassette_count = input_count = response_count = terminal_inputs = 0
    for run in sorted(campaign.glob("cases/*/attempt-*/*/runs/*")):
        boundary = RunManifest.model_validate_json((run / "run-manifest.json").read_bytes())
        assert boundary.mode == "live"
        assert semantic_hash(boundary.identity) == boundary.boundary_sha256
        assert boundary.identity.fast_agent_version == version("fast-agent-mcp")
        assert boundary.identity.pydantic_version == version("pydantic")
        for name, digest in boundary.identity.inputs.items():
            if name not in frozen_inputs:
                frozen_inputs[name] = sha256_bytes((ROOT / name).read_bytes())
            assert frozen_inputs[name] == digest, name
        # Startup infrastructure failures legitimately have no model response.
        # The playback loader intentionally refuses an empty response corpus.
        cassette_files = tuple((run / "cassettes").glob("*.json"))
        cassettes = load_cassettes(run) if cassette_files else ()
        input_files = sorted((run / "model").glob("*.input.json"))
        response_files = sorted((run / "model").glob("*.response.json"))
        cassette_count += len(cassettes)
        input_count += len(input_files)
        response_count += len(response_files)
        assert len(cassettes) == len(response_files)
        if not (run / "terminal.json").exists():
            interrupted = validated_interruption(run, ROOT)
            assert interrupted is not None
            note, annotation = interrupted
            interruptions.append(
                {
                    "run_path": note.run_path,
                    "reason": note.reason,
                    "recorded_responses": len(response_files),
                    "recorded_inputs": len(input_files),
                    "annotation_sha256": sha256_bytes(annotation.read_bytes()),
                    "unanswered_provider_usage": None,
                }
            )
            continue
        terminal = json.loads((run / "terminal.json").read_bytes())
        terminal_counts[terminal["status"]] += 1
        terminal_inputs += len(input_files)
        assert terminal["model_decisions"] == len(cassettes)
        assert set(terminal["cassette_hashes"]) == {p.stem for p in (run / "cassettes").glob("*.json")}
        for name, digest in terminal["cassette_hashes"].items():
            assert sha256_bytes((run / "cassettes" / f"{name}.json").read_bytes()) == digest
        record_path = run.parent.parent / "record.json"
        record = json.loads(record_path.read_bytes())
        assert record["execution_key"] == boundary.boundary_sha256
        if terminal["status"] == "failed":
            physical_failure_codes[terminal["code"]] += 1
            assert not (run / "output.json").exists()
    runtime = json.loads((campaign / "runtime.json").read_bytes())
    assert runtime["physical_analysis_attempts"] == sum(terminal_counts.values())
    assert sum(runtime["model_calls_by_role"].values()) == terminal_inputs
    assert runtime["source_reuse_cases"] == reused_sources
    assert len(interruptions) == 2
    assert sum(item["recorded_responses"] for item in interruptions) == 10
    assert input_count - response_count == 2
    historical = [
        CaseResult.model_validate_json(path.read_bytes())
        for path in sorted(campaign.glob("cases/*/attempt-*/case.json"))
    ]
    old_index = ROOT / "artifacts/verification/restart-recovery-v2/pre-resume-artifact-hashes.json"
    old = json.loads(old_index.read_bytes())
    old_checked = 0
    for name, digest in old.items():
        if name == str((campaign / "progress.json").relative_to(ROOT)):
            continue
        assert sha256_bytes((ROOT / name).read_bytes()) == digest, name
        old_checked += 1
    write_json(
        packet / "audit.json",
        {
            "status": "verified_complete_capture_and_independent_outcome_counts",
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "logical_comparisons": len(cases),
            "distinct_mr_base_panels": len(specs),
            "rows": independent_counts,
            "unique_terminal_runs_referenced_by_latest_cases": len(physical_references),
            "all_physical_terminal_statuses": dict(sorted(terminal_counts.items())),
            "all_physical_failure_codes": dict(sorted(physical_failure_codes.items())),
            "historical_attempt_case_statuses": dict(sorted(Counter(c.status for c in historical).items())),
            "source_reuse_cases": reused_sources,
            "all_saved_model_inputs": input_count,
            "all_saved_model_responses": response_count,
            "validated_cassettes": cassette_count,
            "frozen_input_files_verified": len(frozen_inputs),
            "pre_restart_files_reverified": old_checked,
            "interruptions": interruptions,
            "campaign_artifact_files_verified": len(stored_hashes),
            "source_hashes": {
                str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes())
                for p in [
                    Path(__file__),
                    cohort_path,
                    old_index,
                    campaign / "manifest.json",
                    *[campaign / name for name in required],
                ]
            },
            "scope": "Capture integrity and elementary outcome counts. Not full offline playback, fresh sampling, causal diagnosis or assignment completion.",
        },
    )
    print(
        f"Verified {len(cases)} comparisons / {len(specs)} base panels; "
        f"{sum(terminal_counts.values())} terminal runs and {len(interruptions)} preserved interruptions; "
        f"{cassette_count} cassettes; {old_checked} pre-restart files unchanged."
    )


if __name__ == "__main__":
    main()
