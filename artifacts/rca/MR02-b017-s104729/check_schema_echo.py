"""Verify a fresh source's schema echo against its exact captured role instruction."""

import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from housing.data.generate import CSV_PATH
from housing.evaluation.models import CaseResult
from housing.identity import ROOT, sha256_bytes

destination = Path(__file__).resolve().parent
case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR02-b017-s104729/result.json"
earlier_case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR01-b017-s104729/result.json"
case = CaseResult.model_validate_json(case_path.read_bytes())
earlier = CaseResult.model_validate_json(earlier_case_path.read_bytes())
assert case.source.status == earlier.source.status == "failed"
assert case.source.execution_key == earlier.source.execution_key
assert case.source_reused_from is None and case.followup.status == "completed"
assert case.source.view_sha256 == sha256_bytes(CSV_PATH.read_bytes())
capture = ROOT / case.source.run_path
events = [json.loads(line) for line in (capture / "trace.jsonl").read_text().splitlines()]
invalid = [event for event in events if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False]
assert [event["sequence"] for event in invalid] == [11, 13]
assert all(event["actor"] == "reviewer" for event in invalid)
assert invalid[0]["payload"]["raw"] == invalid[1]["payload"]["raw"]
responses = []
support = [case_path, earlier_case_path, capture / "terminal.json", capture / "trace.jsonl", CSV_PATH]
for sequence, event in zip((6, 8), invalid, strict=True):
    input_path = capture / "model" / f"{sequence:03}.input.json"
    response_path = capture / "model" / f"{sequence:03}.response.json"
    payload = json.loads(input_path.read_bytes())
    response = json.loads(response_path.read_bytes())
    raw = next(item["text"] for item in response["content"] if item["type"] == "text")
    assert raw == event["payload"]["raw"]
    assert payload["instruction"].endswith(raw)
    digest = sha256_bytes(raw.encode())
    assert digest == payload["role_schema_sha256"]
    schema = json.loads(raw)
    assert "role" not in schema and schema["properties"]["role"]["const"] == "reviewer"
    responses.append({"ordinal": sequence, "raw_response_sha256": digest,
                      "exact_instruction_schema_suffix": True,
                      "validation_errors": event["payload"]["errors"]})
    support.extend([input_path, response_path])
parent_calls = []
repair_candidate = None
for sequence in (5, 7):
    path = capture / "cassettes" / f"{sequence:03}.json"
    cassette = json.loads(path.read_bytes())
    calls = [cassette["response"]["tool_calls"][key]["params"]["name"]
             for key in cassette["response_tool_call_order"]]
    assert calls == ["agent__reviewer"]
    parent_calls.append({"ordinal": sequence, "tools": calls})
    if sequence == 7:
        tool = cassette["response"]["tool_calls"][cassette["response_tool_call_order"][0]]
        repair_candidate = json.loads(tool["params"]["arguments"]["message"])
        Draft202012Validator(schema).validate(repair_candidate)
    support.append(path)
assert any(event["event"] == "AGGREGATE_COMPLETED" and event["sequence"] == 10 for event in events)
assert not any(event["event"] == "REVIEW_DECIDED" for event in events)
assert not (capture / "output.json").exists()
comparison_path = destination / "20261004T165129Z/comparison.json"
comparison = json.loads(comparison_path.read_bytes())
assert comparison["status"] == "matched" and comparison["model_decisions"] == 9
assert comparison["network_attempts"] == []
replay = ROOT / comparison["replay"]
terminal = json.loads((replay / "terminal.json").read_bytes())
assert terminal["code"] == "AGENT_OUTPUT_INVALID" and terminal["stage"] == "REVIEW_REQUIRED"
assert not (replay / "output.json").exists()
for role in ("price", "supply", "region"):
    relative = Path("tools/iteration-0") / f"{role}_stats.result.json"
    assert json.loads((capture / relative).read_bytes()) == json.loads((replay / relative).read_bytes())
    support.extend([capture / relative, replay / relative])
support.append(comparison_path)
packet = {
    "checked_at_utc": datetime.now(UTC).isoformat(),
    "scope": "Preliminary source-leg recurrence of the known schema-echo mechanism; no new live sample, distinct-bug or final-ranking claim.",
    "case": str(case_path.relative_to(ROOT)), "source_reused_from": None,
    "same_source_execution_key_as_earlier_MR01_case": True,
    "source_view_is_frozen_untransformed_csv": True,
    "followup_status": case.followup.status, "responses": responses,
    "parent_reviewer_calls": parent_calls, "aggregate_event_sequence": 10,
    "repair_parent_candidate": repair_candidate,
    "repair_parent_candidate_matches_declared_json_schema": True,
    "candidate_is_an_accepted_reviewer_response": False,
    "accepted_review": False, "final_output_published": False,
    "recomputed_tool_results_match": ["price", "supply", "region"],
    "strict_replay_decisions": 9, "network_attempts": [],
    "supporting_artifact_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in support},
}
(destination / "boundary-diagnostic.json").write_text(json.dumps(packet, indent=2) + "\n")
print(json.dumps({key: value for key, value in packet.items() if key != "supporting_artifact_hashes"}, indent=2))
