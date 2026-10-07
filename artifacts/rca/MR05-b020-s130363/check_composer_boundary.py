"""Check a natural missing-caveat failure, source availability and strict playback."""

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.decisions import ReportDecision
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH
from housing.evaluation.models import CaseResult, Cohort
from housing.identity import ROOT, semantic_hash, sha256_bytes

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR05-b020-s130363/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(item for item in cohort.cases if item.mr == "MR05" and item.base_id == "b020")
assert spec.eligibility.eligible and case.source_reused_from is None
assert case.source.status == "failed" and case.followup.status == "completed"
assert case.comparison is None and case.violation_kind == "output_contract"
capture = ROOT / case.source.run_path
request = AnalysisRequest.model_validate_json((capture / "request.json").read_bytes())
assert request == spec.source_request.model_copy(update={"seed": case.seed})
assert case.seed == 130363
assert case.source.view_sha256 == case.followup.view_sha256 == sha256_bytes(CSV_PATH.read_bytes())

# Calendar availability and source counts, independent of production selection/statistics/comparison.
rows = list(csv.DictReader(io.StringIO(CSV_PATH.read_text())))
year, month = map(int, request.window_end.split("-"))
end = year * 12 + month - 1
required = [f"{ordinal // 12:04}-{ordinal % 12 + 1:02}" for ordinal in range(end - 23, end + 1)]
visible = required[12:]
available = {row["month"] for row in rows}
assert len(available) == 24 and min(available) == "2024-10" and max(available) == "2026-09"
unavailable = sorted(set(required) - available)
assert unavailable == ["2024-08", "2024-09"]
counts = {label: 0 for label in visible}
criteria = request.criteria
for row in rows:
    if row["month"] not in counts:
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
    counts[row["month"]] += 1
assert counts == spec.eligibility.witnesses["source_month_counts"]
assert sum(counts.values()) == 26


def events(run):
    return [json.loads(line) for line in (run / "trace.jsonl").read_bytes().splitlines()]


live = events(capture)
assert [event["sequence"] for event in live if event["event"] == "AGGREGATE_COMPLETED"] == [8, 21]
assert live[21]["payload"]["provisional"] is False
assert live[23]["payload"]["decision"]["decision"] == "ACCEPT_LIMITED"
assert live[24]["event"] == "AGENT_DECISION" and live[24]["actor"] == "composer"
assert live[24]["payload"]["valid"] is True
decision = ReportDecision.model_validate(live[24]["payload"]["decision"])
model_input = json.loads((capture / "model/014.input.json").read_bytes())
context = model_input["context"]
assert context["stage"] == "ACCEPTED" and context["iteration"] == 1
assert context["monthly_counts"] == counts
assert set(decision.fact_ids) <= set(context["facts"])
assert set(context["required_caveats"]) == {"SYNTHETIC_DATA", "SPARSE_SUPPORT", "UNAVAILABLE_LOOKBACK"}
assert set(context["required_caveats"]) - set(decision.caveat_codes) == {"UNAVAILABLE_LOOKBACK"}
assert set(decision.caveat_codes) <= set(context["required_caveats"])
parent = json.loads((capture / "cassettes/013.json").read_bytes())
delegation = [parent["response"]["tool_calls"][key]["params"] for key in parent["response_tool_call_order"]]
assert len(delegation) == 1 and delegation[0]["name"] == "agent__composer"
assert "required_caveats: SPARSE_SUPPORT" in delegation[0]["arguments"]["message"]
assert "UNAVAILABLE_LOOKBACK" not in delegation[0]["arguments"]["message"]
assert "caveat_codes exactly required_caveats" in model_input["instruction"]
assert not (capture / "composition.json").exists() and not (capture / "output.json").exists()
assert not any(event["event"] == "AGENT_REPAIR" for event in live)

# Auxiliary boundary reduction: the schema requires four fields and at least one fact.
# It is not a modified capture, model correction or full-system minimized replay.
minimal = ReportDecision.model_validate({"role": "composer", "decision_type": "report",
                                        "fact_ids": ("observations",), "caveat_codes": decision.caveat_codes})
corrected_control = ReportDecision.model_validate(
    {**minimal.model_dump(), "caveat_codes": tuple(context["required_caveats"])})
assert set(minimal.fact_ids) <= set(context["facts"])
assert set(context["required_caveats"]) - set(minimal.caveat_codes) == {"UNAVAILABLE_LOOKBACK"}
assert set(corrected_control.caveat_codes) == set(context["required_caveats"])
minimal_path = destination / "minimal-boundary.json"
minimal_path.write_text(json.dumps({
    "scope": "Constructed boundary-only reduction using the captured trusted context. Not a new live sample, observed model repair, full-system data minimization or successful mitigation campaign.",
    "original_context_sha256": semantic_hash(context),
    "available_fact_ids": sorted(context["facts"]), "required_caveats": context["required_caveats"],
    "schema_valid_minimal_omission": minimal.model_dump(mode="json"),
    "missing_caveats": ["UNAVAILABLE_LOOKBACK"],
    "constructed_complete_caveat_control": corrected_control.model_dump(mode="json"),
    "minimality_limit": "Four fields are required by ReportDecision; one selected fact meets its minimum. The full captured workflow/data have not been minimized.",
}, indent=2) + "\n")

comparison_path = destination / "20261007T061629Z/comparison.json"
comparison = json.loads(comparison_path.read_bytes())
assert comparison["status"] == "matched" and comparison["model_decisions"] == 15
assert comparison["network_attempts"] == []
replay = ROOT / comparison["replay"]
terminal = json.loads((replay / "terminal.json").read_bytes())
assert terminal["code"] == "AGENT_POLICY_ERROR" and terminal["stage"] == "ACCEPTED"
assert not (replay / "composition.json").exists() and not (replay / "output.json").exists()
replayed_context = json.loads((replay / "model/014.input.json").read_bytes())["context"]
assert replayed_context["facts"] == context["facts"]
assert replayed_context["required_caveats"] == context["required_caveats"]
tools = [event for event in events(replay) if event["event"] == "TOOL_COMPLETED"]
assert [(event["actor"], event["iteration"]) for event in tools] == [
    ("price", 0), ("supply", 0), ("price", 1), ("supply", 1), ("region", 1)]
receipt_differences = {}
for event in tools:
    stem = Path(f"tools/iteration-{event['iteration']}/{event['actor']}_stats")
    result, receipt = Path(str(stem) + ".result.json"), Path(str(stem) + ".receipt.json")
    assert json.loads((capture / result).read_bytes()) == json.loads((replay / result).read_bytes())
    recorded = json.loads((capture / receipt).read_bytes())
    recomputed = json.loads((replay / receipt).read_bytes())
    assert recorded["result_sha256"] == recomputed["result_sha256"]
    differences = sorted(key for key in recorded if recorded[key] != recomputed[key])
    assert set(differences) <= {"duration_ms", "partition_receipts_path", "receipt_id", "result_path", "run_id"}
    receipt_differences[str(stem)] = differences
support = [case_path, cohort_path, CSV_PATH, comparison_path, minimal_path, Path(__file__).resolve(),
           ROOT / "src/housing/workflow/controller.py", ROOT / "src/housing/contracts/decisions.py",
           ROOT / "data/manifests/dallas-synth-v1.json",
           capture / "trace.jsonl", capture / "terminal.json", capture / "model/014.input.json",
           capture / "model/014.response.json", capture / "cassettes/013.json"]
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Preliminary natural Composer caveat-omission diagnostic. No numerical pair, causal price-band effect, final rank or successful mitigation claim.",
    "case": str(case_path.relative_to(ROOT)), "source_status": case.source.status,
    "followup_status": case.followup.status, "source_reused_from": case.source_reused_from,
    "source_visible_counts": counts, "source_visible_observations": 26,
    "unavailable_required_months": unavailable, "all_selected_fact_ids_available": True,
    "missing_caveats": ["UNAVAILABLE_LOOKBACK"], "extra_caveats": [],
    "composer_json_schema_valid": True, "composer_policy_valid": False,
    "parent_delegation": delegation[0], "schema_repair_used": False,
    "accepted_review_before_composer": "ACCEPT_LIMITED", "fresh_tool_executions": 5,
    "all_tool_results_match_recorded_json_and_hashes": True,
    "raw_receipt_differences": receipt_differences,
    "strict_replay_decisions": 15, "network_attempts": [],
    "composition_published": False, "final_output_published": False,
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"supporting_artifact_hashes", "parent_delegation", "source_visible_counts"}}, indent=2))
