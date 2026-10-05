"""Check actual replicated rows and the five-decision Supply failure without live calls."""

import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import CaseResult, Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR03-b019-s155921/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(item for item in cohort.cases if item.mr == "MR03" and item.base_id == "b019")
assert spec.eligibility.eligible and case.source_reused_from is None
assert case.source.status == case.followup.status == "failed"
request = updated_request(spec.source_request, seed=case.seed)
source = load_snapshot(CSV_PATH, MANIFEST_PATH)
followup, changed_request = transform(
    source, request, spec.recipe, DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
)
assert changed_request == request
assert source.view_sha256 == case.source.view_sha256 == spec.source_view_sha256
assert followup.view_sha256 == case.followup.view_sha256 == spec.followup_view_sha256
capture = ROOT / case.followup.run_path
assert AnalysisRequest.model_validate_json((capture / "request.json").read_bytes()) == request

original = list(csv.DictReader(io.StringIO(source.raw_csv.decode("utf-8"))))
replicated = list(csv.DictReader(io.StringIO(followup.raw_csv.decode("utf-8"))))
before = {row["record_id"]: row for row in original}
after = {row["record_id"]: row for row in replicated}
assert len(before) == len(original) > 0
assert len(after) == len(replicated) == 2 * len(original)
clone_ids = {"replica-" + key for key in before}
assert set(before).isdisjoint(clone_ids)
assert set(after) == set(before) | clone_ids
for record_id, row in before.items():
    assert after[record_id] == row
    assert after["replica-" + record_id] == {**row, "record_id": "replica-" + record_id}

# Independent raw integer predicates/calendar arithmetic, without production selection/statistics.
year, month = map(int, request.window_end.split("-"))
end = year * 12 + month - 1
visible = [f"{ordinal // 12:04}-{ordinal % 12 + 1:02}" for ordinal in range(end - 11, end + 1)]
criteria = request.criteria


def visible_counts(rows):
    selected = Counter({label: 0 for label in visible})
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
        selected[row["month"]] += 1
    return dict(sorted(selected.items()))


source_counts, followup_counts = visible_counts(original), visible_counts(replicated)
assert sum(source_counts.values()) > 0
assert followup_counts == {month: 2 * count for month, count in source_counts.items()}
assert source_counts == spec.eligibility.witnesses["source_month_counts"]
assert followup_counts == spec.eligibility.witnesses["followup_month_counts"]

events = [json.loads(line) for line in (capture / "trace.jsonl").read_text().splitlines()]
batch = json.loads((capture / "cassettes/001.json").read_bytes())
ordered = [batch["response"]["tool_calls"][key]["params"] for key in batch["response_tool_call_order"]]
assert [call["name"] for call in ordered] == ["agent__price", "agent__supply", "agent__region"]
assert all("purpose public_comparison" in call["arguments"]["message"] for call in ordered[:2])


def decision(sequence):
    response = json.loads((capture / "model" / f"{sequence:03}.response.json").read_bytes())
    return json.loads(next(item["text"] for item in response["content"] if item["type"] == "text"))


price, supply, region = (decision(sequence) for sequence in (2, 3, 4))
assert price["role"] == "price" and price["purpose"] == "statistics"
assert supply["role"] == "supply" and supply["purpose"] == "public_comparison"
assert region["role"] == "region"
tools = [event for event in events if event["event"] == "TOOL_COMPLETED"]
invalid = [event for event in events
           if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False]
assert len(tools) == len(invalid) == 1
assert tools[0]["actor"] == "price" and tools[0]["sequence"] == 5
assert invalid[0]["actor"] == "supply" and invalid[0]["sequence"] == 6
assert invalid[0]["payload"]["errors"][0]["location"] == ["supply", "purpose"]
assert events[7]["event"] == "AGENT_REPAIR" and events[8]["event"] == "RUN_FAILED"
assert not any(event["event"] == "AGGREGATE_COMPLETED" for event in events)
assert not (capture / "output.json").exists()
comparison_path = destination / "20261005T094429Z/comparison.json"
comparison = json.loads(comparison_path.read_bytes())
assert comparison["status"] == "matched" and comparison["model_decisions"] == 5
assert comparison["network_attempts"] == []
replay = ROOT / comparison["replay"]
replayed_events = [json.loads(line) for line in (replay / "trace.jsonl").read_text().splitlines()]
assert not any(event["event"] == "AGGREGATE_COMPLETED" for event in replayed_events)
assert not (replay / "output.json").exists()
result_path = Path("tools/iteration-0/price_stats.result.json")
receipt_path = Path("tools/iteration-0/price_stats.receipt.json")
recorded_result = json.loads((capture / result_path).read_bytes())
replayed_result = json.loads((replay / result_path).read_bytes())
assert recorded_result == replayed_result
recorded_receipt = json.loads((capture / receipt_path).read_bytes())
replayed_receipt = json.loads((replay / receipt_path).read_bytes())
assert recorded_receipt["result_sha256"] == replayed_receipt["result_sha256"]
receipt_differences = sorted(key for key in recorded_receipt
                             if recorded_receipt[key] != replayed_receipt[key])
assert set(receipt_differences) <= {
    "duration_ms", "partition_receipts_path", "receipt_id", "result_path", "run_id"
}
support = [case_path, cohort_path, CSV_PATH, MANIFEST_PATH,
           capture / "trace.jsonl", capture / "terminal.json", capture / "request.json",
           capture / "cassettes/001.json", capture / result_path, capture / receipt_path,
           replay / result_path, replay / receipt_path, comparison_path]
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Preliminary MR03 replication and partial-receipt proof. No new live sample, distinct-bug, numeric pair or final-ranking claim.",
    "case": str(case_path.relative_to(ROOT)),
    "source_status": case.source.status, "source_error_code": case.source.error_code,
    "source_reused_from": case.source_reused_from,
    "source_raw_rows": len(original), "followup_raw_rows": len(replicated),
    "original_rows_retained_exactly": True, "one_collision_free_exact_clone_per_original": True,
    "all_nonrecord_id_fields_preserved": True,
    "source_view_sha256": source.view_sha256, "followup_view_sha256": followup.view_sha256,
    "independent_source_visible_counts": source_counts,
    "independent_followup_visible_counts": followup_counts,
    "source_visible_observations": sum(source_counts.values()),
    "followup_visible_observations": sum(followup_counts.values()),
    "parent_delegations": ordered, "price_decision": price, "supply_decision": supply,
    "next_region_decision": region, "accepted_tools_before_failure": ["price_stats"],
    "price_tool_sequence": 5, "invalid_supply_sequence": 6, "repair_sequence": 7,
    "terminal_sequence": 8, "aggregate_published": False, "final_output_published": False,
    "recorded_price_result_matches_recomputed": True,
    "price_result_sha256": recorded_receipt["result_sha256"],
    "raw_receipt_differences": receipt_differences,
    "strict_replay_decisions": 5, "network_attempts": [],
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes())
                                  for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"supporting_artifact_hashes", "parent_delegations",
                                 "independent_source_visible_counts", "independent_followup_visible_counts"}},
                 indent=2))
