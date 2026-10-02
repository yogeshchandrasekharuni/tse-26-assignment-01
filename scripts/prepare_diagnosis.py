"""Index actual top violated relations for review; never manufacture a verified diagnosis."""

import argparse
import json
import re
from fractions import Fraction

from housing.evaluation.models import CaseResult, HeadlineRow
from housing.identity import ROOT, sha256_bytes, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="headline-live-v1")
    args = parser.parse_args()
    if re.fullmatch(r"[A-Za-z0-9-]+", args.campaign) is None:
        raise ValueError("Campaign must be a local identifier")
    directory = ROOT / "artifacts/campaigns" / args.campaign
    headline_path = directory / "headline.json"
    rows = [HeadlineRow.model_validate(row) for row in json.loads(headline_path.read_bytes())]
    if not rows or not all(row.complete for row in rows):
        raise ValueError("Diagnosis ranking requires a completed campaign, never a partial favorable slice")
    ranked = sorted(
        rows,
        key=lambda row: (-Fraction(row.base_rate or "0"), -row.violating_bases, row.mr_id),
    )
    cases = [
        CaseResult.model_validate_json(line) for line in (directory / "cases.jsonl").read_text().splitlines()
    ]
    selected = []
    for row in [item for item in ranked if item.violating_bases > 0][:3]:
        failures = sorted(
            (case for case in cases if case.mr_id == row.mr_id and case.status == "violation"),
            key=lambda case: (case.base_id, case.seed),
        )
        representative = failures[0]
        neighbors = sorted(
            (case for case in cases if case.mr_id == row.mr_id and case.status == "pass"),
            key=lambda case: (case.base_id != representative.base_id, case.base_id, case.seed),
        )
        legs = []
        for label, leg in (("source", representative.source), ("followup", representative.followup)):
            run = (ROOT / leg.run_path).resolve()
            if not run.is_relative_to(ROOT / "artifacts/campaigns"):
                raise ValueError("Run path escapes the campaign evidence registry")
            trace_path = run / "trace.jsonl"
            events = [json.loads(line) for line in trace_path.read_text().splitlines()]
            first_invalid = next(
                (
                    event
                    for event in events
                    if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False
                ),
                None,
            )
            failure_path = run / "failure.json"
            failure = json.loads(failure_path.read_bytes()) if failure_path.exists() else None
            legs.append(
                {
                    "leg": label,
                    "run_path": leg.run_path,
                    "terminal": leg.status,
                    "error_code": leg.error_code,
                    "error_stage": leg.error_stage,
                    "failure_message": failure["message"] if failure else None,
                    "first_invalid_decision": first_invalid,
                    "trace_sha256": sha256_bytes(trace_path.read_bytes()),
                }
            )
        selected.append(
            {
                "mr_id": row.mr_id,
                "headline": row,
                "representative_selection": "lexicographically first failing base, then seed; no outcome-based replacement",
                "representative": representative,
                "passing_neighbor": neighbors[0] if neighbors else None,
                "legs": legs,
                "first_numeric_difference": representative.comparison.differences[0]
                if representative.comparison and representative.comparison.differences
                else None,
                "required_review": [
                    "Inspect original request, raw transformation witness, decisions and receipts",
                    "Distinguish agent/aggregation, concrete data artifact, invalid relation and harness fault",
                    "Preserve original and a justified minimized reproducer; replay actual failure",
                    "Record competing explanations, any versioned correction and remaining uncertainty",
                ],
            }
        )
    output = ROOT / "reports/data" / f"{args.campaign}-diagnosis-candidates.json"
    write_json(
        output,
        {
            "status": "requires_review",
            "campaign_id": directory.name,
            "headline_sha256": sha256_bytes(headline_path.read_bytes()),
            "cases_sha256": sha256_bytes((directory / "cases.jsonl").read_bytes()),
            "rank_rule": "base-level rate descending, violating bases descending, MR ID ascending",
            "ranked_relations": [row.mr_id for row in ranked],
            "nonzero_relations": sum(row.violating_bases > 0 for row in rows),
            "selected": selected,
            "interpretation": "Candidate evidence index, not a verified causal diagnosis or a new experiment",
        },
    )
    print(
        f"Indexed {len(selected)} naturally violated relation(s); review required. {output.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
