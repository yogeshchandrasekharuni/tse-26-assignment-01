"""Build headline statistics from immutable logical cases, with base units and lineage checks."""

import csv
import io
import json
from collections import Counter
from pathlib import Path

from housing.evaluation.models import CaseResult, Cohort, HeadlineRow, MRId
from housing.evaluation.statistics import wilson
from housing.identity import ROOT, canonical_json, semantic_hash, sha256_bytes, write_json

FAMILIES: dict[MRId, str] = {
    "MR01": "invariance",
    "MR02": "invariance",
    "MR03": "invariance",
    "MR04": "invariance",
    "MR05": "monotonic",
    "MR06": "monotonic",
    "MR07": "directional",
    "MR08": "directional",
    "MR09": "monotonic",
    "MR10": "invariance",
}


def case_semantics(case: CaseResult) -> dict[str, object]:
    """Only run/mode/duration/path identity is excluded from live/replay comparison."""
    return {
        "mr_id": case.mr_id,
        "mr_version": case.mr_version,
        "base_id": case.base_id,
        "base_semantic_sha256": case.base_semantic_sha256,
        "cohort_case_sha256": case.cohort_case_sha256,
        "transform_sha256": case.transform_sha256,
        "seed": case.seed,
        "status": case.status,
        "violation_kind": case.violation_kind,
        "reason_codes": case.reason_codes,
        "comparison": case.comparison,
        "legs": [
            {
                key: getattr(leg, key)
                for key in (
                    "execution_key",
                    "status",
                    "request_sha256",
                    "view_sha256",
                    "requested_seed",
                    "effective_seed",
                    "canonical_sha256",
                    "error_code",
                    "error_stage",
                )
            }
            for leg in (case.source, case.followup)
        ],
    }


def aggregate(
    directory: Path, *, require_complete: bool = True, minimum_bases: int = 30
) -> list[dict[str, object]]:
    manifest = json.loads((directory / "manifest.json").read_bytes())
    cohort_path = ROOT / manifest["cohort_path"]
    if sha256_bytes(cohort_path.read_bytes()) != manifest["cohort_sha256"]:
        raise ValueError("Cohort integrity differs")
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    expected = {(c.mr, c.base_id, seed): c for c in cohort.cases for seed in cohort.seeds}
    records: dict[tuple[MRId, str, int], CaseResult] = {}
    seen_sources: dict[str, str] = {}
    followups: set[str] = set()
    for path in sorted((directory / "cases").glob("*/result.json")):
        case = CaseResult.model_validate_json(path.read_bytes())
        key = case.mr_id, case.base_id, case.seed
        if key not in expected or key in records:
            raise ValueError("Unexpected or duplicate logical comparison")
        spec = expected[key]
        if (
            case.campaign_id != directory.name
            or case.mode != manifest["mode"]
            or case.cohort_case_sha256 != semantic_hash(spec)
        ):
            raise ValueError("Case campaign/cohort lineage differs")
        if case.base_semantic_sha256 != spec.base_query_sha256 or case.transform_sha256 != semantic_hash(
            spec.recipe
        ):
            raise ValueError("Case source/transform identity differs")
        for leg, view in ((case.source, spec.source_view_sha256), (case.followup, spec.followup_view_sha256)):
            if leg.requested_seed != case.seed or leg.view_sha256 != view:
                raise ValueError("Pair seed/view lineage differs")
            if leg.status == "completed" and (
                leg.error_code is not None or leg.effective_seed != case.seed or leg.canonical_sha256 is None
            ):
                raise ValueError("Completed leg has inconsistent seed/error/output metadata")
        if case.source.run_id in seen_sources and (
            seen_sources[case.source.run_id] != case.source.execution_key or case.source_reused_from is None
        ):
            raise ValueError("Source reuse lacks identical execution key and explicit lineage")
        seen_sources[case.source.run_id] = case.source.execution_key
        if case.followup.run_id in followups:
            raise ValueError("A logical follow-up reused another follow-up execution")
        followups.add(case.followup.run_id)
        if case.status == "pass" and (
            case.comparison is None or case.comparison.status != "pass" or case.reason_codes
        ):
            raise ValueError("Pass lacks a successful eligible comparison")
        if case.status == "violation" and case.violation_kind is None:
            raise ValueError("Violation lacks subtype")
        records[key] = case
    missing = sorted(set(expected) - set(records))
    base_rows: list[dict[str, object]] = []
    headline: list[dict[str, object]] = []
    for mr in sorted({c.mr for c in cohort.cases}):
        specs = [c for c in cohort.cases if c.mr == mr]
        if len({c.base_query_sha256 for c in specs}) != len(specs):
            raise ValueError("MR cohort contains duplicate semantic bases")
        group = [r for key, r in records.items() if key[0] == mr]
        completed_bases = violating_bases = 0
        for spec in specs:
            panel = [records.get((mr, spec.base_id, seed)) for seed in cohort.seeds]
            complete = all(r is not None and r.status != "execution_error" for r in panel)
            any_violation = (
                any(r is not None and r.status == "violation" for r in panel) if complete else None
            )
            completed_bases += int(complete)
            violating_bases += int(bool(any_violation))
            base_rows.append(
                {
                    "mr_id": mr,
                    "base_id": spec.base_id,
                    "base_semantic_sha256": spec.base_query_sha256,
                    "slice_group": spec.slice_group,
                    "window_end": spec.source_request.window_end,
                    "completed": complete,
                    "any_seed_violation": any_violation,
                    "seed_panel": [
                        {"seed": seed, "status": result.status if result else "missing"}
                        for seed, result in zip(cohort.seeds, panel, strict=True)
                    ],
                }
            )
        rate, low, high = wilson(violating_bases, completed_bases)
        errors = sum(r.status == "execution_error" for r in group)
        headline.append(
            {
                "schema_version": "headline-2",
                "mr_id": mr,
                "family": FAMILIES[mr],
                "mode": manifest["mode"],
                "campaign_id": directory.name,
                "live_campaign_id": manifest["live_campaign_id"],
                "eligible_bases": len(specs),
                "completed_bases": completed_bases,
                "violating_bases": violating_bases,
                "base_rate": rate,
                "ci_method": "wilson_score",
                "ci_unit": "distinct_completed_eligible_base",
                "ci95_low": low,
                "ci95_high": high,
                "seed_values": list(cohort.seeds),
                "seed_pair_violations": sum(r.status == "violation" for r in group),
                "seed_pairs_completed": sum(r.status != "execution_error" for r in group),
                "invalid_candidates": sum(c.mr == mr for c in cohort.invalid_candidates),
                "execution_errors": errors,
                "output_contract_violations": sum(r.violation_kind == "output_contract" for r in group),
                "complete": completed_bases >= minimum_bases
                and completed_bases == len(specs)
                and errors == 0,
                "interpretation": "Nominal base-level Wilson interval for an overlapping designed workload and fixed seed panel; generalization limited",
            }
        )
    ordered_cases = [records[key] for key in sorted(records)]
    for row in headline:
        HeadlineRow.model_validate_json(canonical_json(row))
    (directory / "cases.jsonl").write_text("".join(canonical_json(case) + "\n" for case in ordered_cases))
    (directory / "base_summary.jsonl").write_text("".join(canonical_json(row) + "\n" for row in base_rows))
    write_json(directory / "headline.json", headline)
    write_json(directory / "coverage.json", cohort.coverage)
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=list(headline[0]))
    writer.writeheader()
    writer.writerows(headline)
    (directory / "headline.csv").write_text(csv_buffer.getvalue())
    role_counts: Counter[str] = Counter()
    repairs = refinements = duration_ns = physical = 0
    for record_path in sorted((directory / "cases").glob("**/record.json")):
        leg = json.loads(record_path.read_bytes())
        physical += 1
        duration_ns += leg["duration_ns"]
        run = ROOT / leg["run_path"]
        for input_path in (run / "model").glob("*.input.json"):
            role_counts[json.loads(input_path.read_bytes())["agent"].split("[", 1)[0]] += 1
        if (run / "trace.jsonl").exists():
            for line in (run / "trace.jsonl").read_text().splitlines():
                event = json.loads(line)
                repairs += int(event["event"] == "AGENT_REPAIR")
                refinements += int(event["event"] == "REFINEMENT_APPLIED")
    write_json(
        directory / "runtime.json",
        {
            "logical_comparisons": len(records),
            "logical_legs": 2 * len(records),
            "physical_analysis_attempts": physical,
            "source_reuse_cases": sum(r.source_reused_from is not None for r in records.values()),
            "model_calls_by_role": dict(role_counts),
            "schema_repairs": repairs,
            "refinements": refinements,
            "sum_analysis_duration_ns": duration_ns,
            "cost": "Local Ollama inference; no monetary price assigned",
            "missing_keys": missing,
        },
    )
    if manifest["mode"] == "replay":
        reference = ROOT / manifest["live_reference"]
        for key, case in records.items():
            live = CaseResult.model_validate_json(
                (reference / "cases" / f"{key[0]}-{key[1]}-s{key[2]}" / "result.json").read_bytes()
            )
            if semantic_hash(case_semantics(case)) != semantic_hash(case_semantics(live)):
                raise ValueError(f"Recomputed live/replay case semantics differ: {key}")
        live_headline = json.loads((reference / "headline.json").read_bytes())
        ignored = {"mode", "campaign_id"}
        if [{k: v for k, v in row.items() if k not in ignored} for row in headline] != [
            {k: v for k, v in row.items() if k not in ignored} for row in live_headline
        ]:
            raise ValueError("Recomputed headline differs from live reference")
        write_json(
            directory / "reproduction-comparison.json",
            {
                "status": "matched",
                "live_reference": str(reference.relative_to(ROOT)),
                "logical_comparisons": len(records),
                "headline_sha256": semantic_hash(headline),
            },
        )
    excluded = {"artifact_hashes.json"}
    hashes = {
        str(p.relative_to(directory)): sha256_bytes(p.read_bytes())
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p.name not in excluded
    }
    write_json(directory / "artifact_hashes.json", hashes)
    if require_complete and (missing or not all(row["complete"] for row in headline)):
        raise ValueError(
            "Campaign incomplete: missing pairs, unresolved infrastructure errors or insufficient completed bases"
        )
    return headline
