"""Bind the observed Supply-purpose variant, recomputed Price result and stopped aggregate."""

import json
from datetime import UTC, datetime
from pathlib import Path

from housing.evaluation.models import CaseResult, Cohort
from housing.identity import ROOT, sha256_bytes

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR02-b013-s155921/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(item for item in cohort.cases if item.mr == "MR02" and item.base_id == "b013")
assert spec.eligibility.eligible
capture = ROOT / case.followup.run_path
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
invalid = [event for event in events if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False]
assert len(tools) == len(invalid) == 1
assert tools[0]["actor"] == "price" and tools[0]["sequence"] == 5
assert invalid[0]["actor"] == "supply" and invalid[0]["sequence"] == 6
assert invalid[0]["payload"]["errors"][0]["location"] == ["supply", "purpose"]
assert events[7]["event"] == "AGENT_REPAIR" and events[8]["event"] == "RUN_FAILED"
assert not any(event["event"] == "AGGREGATE_COMPLETED" for event in events)
assert not (capture / "output.json").exists()
comparison_path = destination / "20261004T121917Z/comparison.json"
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
raw_receipt_differences = sorted(key for key in recorded_receipt
                                 if recorded_receipt[key] != replayed_receipt[key])
support = [case_path, cohort_path, capture / "trace.jsonl", capture / "terminal.json",
           capture / "cassettes/001.json", capture / result_path, capture / receipt_path,
           replay / result_path, replay / receipt_path, comparison_path,
           ROOT / "tests/integration/test_failure_playback.py",
           ROOT / "artifacts/verification/partial-receipt-regression-v1/focused.log",
           ROOT / "artifacts/verification/partial-receipt-regression-v1/make-check.log"]
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Preliminary role variant and partial-receipt safety proof; no new live sample, distinct-bug or final-ranking claim.",
    "case": str(case_path.relative_to(ROOT)), "source_status": case.source.status,
    "source_error_code": case.source.error_code, "source_reused_from": case.source_reused_from,
    "parent_delegations": ordered, "price_decision": price, "supply_decision": supply,
    "next_region_decision": region, "accepted_tools_before_failure": ["price_stats"],
    "price_tool_sequence": 5, "invalid_supply_sequence": 6, "repair_sequence": 7,
    "terminal_sequence": 8, "aggregate_published": False, "final_output_published": False,
    "recorded_price_result_matches_recomputed": True,
    "price_result_sha256": recorded_receipt["result_sha256"],
    "raw_receipt_differences": raw_receipt_differences,
    "strict_replay_decisions": 5, "network_attempts": [],
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items()
                  if key not in {"supporting_artifact_hashes", "parent_delegations"}}, indent=2))
