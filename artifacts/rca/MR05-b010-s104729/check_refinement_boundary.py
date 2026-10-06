"""Check a natural post-refinement failure and its independent price-band witness."""

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH
from housing.evaluation.models import CaseResult, Cohort
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.iterations import iteration_labels
from housing.observability.langfuse import project_capture as legacy_projection
from housing.observability.langfuse_plan import project_capture

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR05-b010-s104729/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(item for item in cohort.cases if item.mr == "MR05" and item.base_id == "b010")
assert spec.eligibility.eligible and case.source_reused_from is None
assert case.source.status == "completed" and case.followup.status == "failed"
assert case.comparison is None and case.violation_kind == "output_contract"
source, capture = ROOT / case.source.run_path, ROOT / case.followup.run_path
requests = [AnalysisRequest.model_validate_json((run / "request.json").read_bytes())
            for run in (source, capture)]
assert requests == [request.model_copy(update={"seed": case.seed})
                    for request in (spec.source_request, spec.followup_request)]
assert requests[0].model_dump(exclude={"criteria"}) == requests[1].model_dump(exclude={"criteria"})
assert requests[0].criteria.model_dump(exclude={"price_min_cents", "price_max_cents"}) == (
    requests[1].criteria.model_dump(exclude={"price_min_cents", "price_max_cents"}))
assert requests[0].criteria.price_min_cents == 20000000
assert requests[0].criteria.price_max_cents == 45000000
assert requests[1].criteria.price_min_cents == 10000000
assert requests[1].criteria.price_max_cents == 75000000
assert case.source.view_sha256 == case.followup.view_sha256 == sha256_bytes(CSV_PATH.read_bytes())

# Raw integer/calendar predicates, independent of production selection/statistics/MR comparison.
rows = list(csv.DictReader(io.StringIO(CSV_PATH.read_text())))
year, month = map(int, requests[0].window_end.split("-"))
end = year * 12 + month - 1
visible = [f"{ordinal // 12:04}-{ordinal % 12 + 1:02}" for ordinal in range(end - 11, end + 1)]


def selected_ids(request):
    criteria = request.criteria
    selected = {label: set() for label in visible}
    for row in rows:
        if row["month"] not in selected:
            continue
        if row["zip"] not in criteria.zips or row["property_type"] not in criteria.property_types:
            continue
        bedrooms, price, area = (int(row[key]) for key in ("bedrooms", "price_cents", "sqft"))
        if not criteria.bedrooms_min <= bedrooms <= criteria.bedrooms_max:
            continue
        if any((low is not None and value < low) or (high is not None and value > high)
               for value, low, high in ((price, criteria.price_min_cents, criteria.price_max_cents),
                                        (area, criteria.sqft_min, criteria.sqft_max))):
            continue
        selected[row["month"]].add(row["record_id"])
    return selected


before, after = (selected_ids(request) for request in requests)
assert all(before[label] <= after[label] for label in visible)
assert any(before[label] < after[label] for label in visible)
counts = [{label: len(ids) for label, ids in selected.items()} for selected in (before, after)]
assert counts[0] == spec.eligibility.witnesses["source_month_counts"]
assert counts[1] == spec.eligibility.witnesses["followup_month_counts"]


def events(run):
    return [json.loads(line) for line in (run / "trace.jsonl").read_bytes().splitlines()]


live_events = events(capture)
assert [event["sequence"] for event in live_events if event["event"] == "AGGREGATE_COMPLETED"] == [8]
assert [event["sequence"] for event in events(source)
        if event["event"] == "AGGREGATE_COMPLETED"] == [8, 21]
assert (source / "output.json").is_file() and not (capture / "output.json").exists()
refinement = live_events[14]
assert refinement["event"] == "REFINEMENT_APPLIED" and refinement["iteration"] == 1
payload = refinement["payload"]
assert payload["criteria_hash_before"] == payload["criteria_hash_after"]
assert payload["before"]["scan_strategy"] == "indexed"
assert payload["before"]["active_specialists"] == ["price", "supply"]
assert payload["after"]["scan_strategy"] == "full_csv"
assert payload["after"]["active_specialists"] == ["price", "supply", "region"]
assert payload["after"]["region_purpose"] == "coverage_diagnostic"
assert live_events[15]["payload"]["valid"] is False
assert live_events[15]["actor"] == "price" and live_events[15]["iteration"] == 1
assert live_events[16]["event"] == "AGENT_REPAIR" and live_events[16]["iteration"] == 0
assert live_events[17]["event"] == "RUN_FAILED" and live_events[17]["iteration"] == 1
assert not any(event["event"] == "TOOL_COMPLETED" and event["iteration"] == 1 for event in live_events)
batch = json.loads((capture / "cassettes/007.json").read_bytes())
ordered = [batch["response"]["tool_calls"][key]["params"] for key in batch["response_tool_call_order"]]
assert [call["name"] for call in ordered] == ["agent__price", "agent__supply", "agent__region"]
assert all("coverage_diagnostic purpose" in call["arguments"]["message"] for call in ordered[:2])
price_response = json.loads((capture / "model/008.response.json").read_bytes())
price = json.loads(next(item["text"] for item in price_response["content"] if item["type"] == "text"))
assert price["role"] == "price" and price["purpose"] == "coverage_diagnostic"
labels = iteration_labels(live_events)
assert [(index, label.display_iteration) for index, label in enumerate(labels)
        if label.basis != "recorded"] == [(16, 1)]

comparison_path = destination / "20261006T180443Z/comparison.json"
comparison = json.loads(comparison_path.read_bytes())
assert comparison["status"] == "matched" and comparison["model_decisions"] == 10
assert comparison["network_attempts"] == []
replay = ROOT / comparison["replay"]
terminal = json.loads((replay / "terminal.json").read_bytes())
assert terminal["code"] == "AGENT_POLICY_ERROR" and terminal["stage"] == "SCANNING"
assert [event["sequence"] for event in events(replay) if event["event"] == "AGGREGATE_COMPLETED"] == [8]
assert not any(event["event"] == "TOOL_COMPLETED" and event["iteration"] == 1 for event in events(replay))
assert not (replay / "output.json").exists()
receipt_differences = {}
for tool in ("price_stats", "supply_stats"):
    result = Path(f"tools/iteration-0/{tool}.result.json")
    receipt = Path(f"tools/iteration-0/{tool}.receipt.json")
    assert json.loads((capture / result).read_bytes()) == json.loads((replay / result).read_bytes())
    recorded = json.loads((capture / receipt).read_bytes())
    recomputed = json.loads((replay / receipt).read_bytes())
    assert recorded["result_sha256"] == recomputed["result_sha256"]
    differences = sorted(key for key in recorded if recorded[key] != recomputed[key])
    assert set(differences) <= {"duration_ms", "partition_receipts_path", "receipt_id", "result_path", "run_id"}
    receipt_differences[tool] = differences

legacy, corrected = legacy_projection(capture), project_capture(capture)
repair = next(span for span in corrected.spans if span.key.endswith("/event-016"))
assert repair.parent_key.endswith("/agent-008")
assert repair.attributes["langfuse.observation.metadata.recorded_iteration"] == 0
assert repair.attributes["langfuse.observation.metadata.iteration"] == 1
assert corrected.trace_id != legacy.trace_id
assert {legacy.span_id(span.key) for span in legacy.spans}.isdisjoint(
    corrected.span_id(span.key) for span in corrected.spans)
projection_path = destination / "plan-projection.json"
projection_path.write_text(json.dumps(corrected.model_dump(mode="json"), indent=2) + "\n")
support = [case_path, cohort_path, CSV_PATH, comparison_path, projection_path, Path(__file__).resolve(),
           source / "trace.jsonl", capture / "trace.jsonl", capture / "terminal.json",
           capture / "cassettes/007.json", capture / "model/008.response.json"]
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Preliminary natural refinement-failure diagnostic; no new live sample, numerical pair, distinct-bug or final-ranking claim. The corrected dashboard projection is prepared offline only.",
    "case": str(case_path.relative_to(ROOT)),
    "source_status": case.source.status, "followup_status": case.followup.status,
    "source_reused_from": case.source_reused_from,
    "independent_source_visible_counts": counts[0], "independent_followup_visible_counts": counts[1],
    "source_visible_observations": sum(counts[0].values()),
    "followup_visible_observations": sum(counts[1].values()),
    "all_source_ids_retained_per_month": True, "nonvacuous_expansion": True,
    "criteria_unchanged_on_refinement": payload["criteria_hash_after"],
    "parent_delegations": ordered, "invalid_price_decision": price,
    "initial_price_and_supply_recomputed_exactly": True,
    "raw_receipt_differences": receipt_differences,
    "second_pass_accepted_tools": [], "second_aggregate_published": False, "final_output_published": False,
    "strict_replay_decisions": 10, "network_attempts": [],
    "repair_recorded_iteration": 0, "repair_display_iteration": 1,
    "legacy_projection_trace_id": legacy.trace_id, "plan_projection_trace_id": corrected.trace_id,
    "plan_projection_sha256": semantic_hash(corrected), "plan_projection_delivered": False,
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"supporting_artifact_hashes", "parent_delegations",
                                 "independent_source_visible_counts", "independent_followup_visible_counts"}}, indent=2))
