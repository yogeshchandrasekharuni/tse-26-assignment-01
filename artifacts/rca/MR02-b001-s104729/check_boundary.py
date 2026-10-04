"""Actual MR02 raw-data and first-divergence evidence; no live inference or rate estimate."""

import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import CaseResult, Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR02-b001-s104729/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(item for item in cohort.cases if item.mr == "MR02" and item.base_id == "b001")
request = updated_request(spec.source_request, seed=case.seed)
source = load_snapshot(CSV_PATH, MANIFEST_PATH)
followup, changed_request = transform(
    source, request, spec.recipe, DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
)
assert changed_request == request
assert source.view_sha256 == case.source.view_sha256
assert followup.view_sha256 == case.followup.view_sha256
original = list(csv.DictReader(io.StringIO(source.raw_csv.decode("utf-8"))))
changed = list(csv.DictReader(io.StringIO(followup.raw_csv.decode("utf-8"))))
assert len(original) == len(changed) == 34560
forward = {field: {} for field in ("record_id", "listing_id")}
reverse = {field: {} for field in forward}
changed_ids = Counter()
for before, after in zip(original, changed, strict=True):
    assert {key: value for key, value in before.items() if key not in forward} == {
        key: value for key, value in after.items() if key not in forward
    }
    for field in forward:
        old, new = before[field], after[field]
        assert forward[field].setdefault(old, new) == new
        assert reverse[field].setdefault(new, old) == old
        changed_ids[field] += old != new
assert all(changed_ids[field] > 0 for field in forward)

# Independent raw predicates/calendar arithmetic: no production selector, median or comparator.
end_year, end_month = map(int, request.window_end.split("-"))
end = end_year * 12 + end_month - 1
criteria = request.criteria

def counts(rows):
    selected = Counter()
    for row in rows:
        year, month = map(int, row["month"].split("-"))
        if not end - 11 <= year * 12 + month - 1 <= end:
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

source_counts, followup_counts = counts(original), counts(changed)
assert source_counts == followup_counts == spec.eligibility.witnesses["source_month_counts"]
assert sum(source_counts.values()) == 2880

capture = ROOT / case.followup.run_path
events = [json.loads(line) for line in (capture / "trace.jsonl").read_text().splitlines()]
parent = json.loads((capture / "model/001.response.json").read_bytes())
price_message = next(call["params"]["arguments"]["message"]
                     for call in parent["tool_calls"].values()
                     if call["params"]["name"] == "agent__price")
assert "purpose public_comparison" in price_message
batch = json.loads((capture / "cassettes/001.json").read_bytes())
native_order = [batch["response"]["tool_calls"][key]["params"]["name"]
                for key in batch["response_tool_call_order"]]
assert native_order == ["agent__price", "agent__supply", "agent__region"]
supply_response = json.loads((capture / "model/003.response.json").read_bytes())
supply_decision = json.loads(next(item["text"] for item in supply_response["content"]
                                  if item["type"] == "text"))
assert supply_decision["role"] == "supply" and supply_decision["purpose"] == "statistics"
invalid = events[4]["payload"]
assert events[4]["event"] == "AGENT_DECISION" and invalid["valid"] is False
assert json.loads(invalid["raw"])["purpose"] == "public_comparison"
assert invalid["errors"][0]["location"] == ["price", "purpose"]
assert invalid["errors"][0]["type"] == "literal_error"
assert events[5]["event"] == "AGENT_REPAIR" and events[6]["event"] == "RUN_FAILED"
assert not any(event["event"] == "TOOL_COMPLETED" for event in events)
comparison_path = destination / "20261004T054210Z/comparison.json"
comparison = json.loads(comparison_path.read_bytes())
assert comparison["status"] == "matched" and comparison["model_decisions"] == 4
assert comparison["network_attempts"] == []
replayed_terminal = json.loads((ROOT / comparison["replay"] / "terminal.json").read_bytes())
assert replayed_terminal["stage"] == case.followup.error_stage == "SCANNING"

support = [case_path, cohort_path, capture / "terminal.json", capture / "trace.jsonl",
           capture / "model/001.response.json", capture / "model/002.response.json",
           capture / "model/003.response.json", capture / "cassettes/001.json",
           ROOT / case.source_reused_from, comparison_path]
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(), "scope": "Preliminary single-case diagnosis, not a final rank/rate or new model sample.",
    "case": str(case_path.relative_to(ROOT)), "transformation": "MR02 nominal-ID relabeling",
    "raw_rows_checked": len(original), "nonidentity_fields_equal_per_row": True,
    "bijections": {field: {"distinct_old": len(forward[field]), "distinct_new": len(reverse[field]),
                            "changed_rows": changed_ids[field]} for field in forward},
    "independent_visible_counts": source_counts, "qualifying_observations_each": 2880,
    "source_reused_from": case.source_reused_from,
    "first_invalid_sequence": 4, "parent_price_message": price_message,
    "native_child_order": native_order, "next_child_decision": supply_decision,
    "invalid_decision": json.loads(invalid["raw"]), "validation_errors": invalid["errors"],
    "pending_repair_sequence": 5, "terminal_sequence": 6,
    "accepted_statistical_tools": 0, "error_code": case.followup.error_code,
    "error_stage": case.followup.error_stage, "strict_replay_decisions": 4,
    "network_attempts": comparison["network_attempts"],
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"supporting_artifact_hashes", "independent_visible_counts"}}, indent=2))
