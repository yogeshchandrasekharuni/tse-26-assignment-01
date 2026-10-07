"""Check the report's named natural loop against raw CSV and immutable live evidence."""

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.evaluation.models import CaseResult
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json


def main() -> None:
    packet = Path(__file__).resolve().parent
    case_path = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR01-b010-s104729/result.json"
    case = CaseResult.model_validate_json(case_path.read_bytes())
    run = ROOT / case.source.run_path
    request = AnalysisRequest.model_validate_json((run / "request.json").read_bytes())
    output = AnalysisOutput.model_validate_json((run / "output.json").read_bytes())
    trace = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    terminal = json.loads((run / "terminal.json").read_bytes())
    manifest = json.loads((run / "run-manifest.json").read_bytes())
    assert manifest["mode"] == "live" and case.source_reused_from is None
    assert terminal["status"] == "completed" and terminal["model_decisions"] == 16
    assert case.source.output_sha256 == semantic_hash(output)
    assert trace[0]["payload"]["headline_eligible"] is True
    assert not trace[0]["payload"]["injected_index_omissions"]
    assert all(event["illustrative_fixture"] is False for event in trace)

    # Independently filter raw integer columns; do not call the production selector or statistics.
    counts: Counter[str] = Counter()
    criteria = request.criteria
    csv_path = ROOT / "data/frozen/dallas-synth-v1.csv"
    with csv_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["month"] not in request.required_months:
                continue
            if row["zip"] not in criteria.zips or row["property_type"] not in criteria.property_types:
                continue
            if not criteria.bedrooms_min <= int(row["bedrooms"]) <= criteria.bedrooms_max:
                continue
            bounds = (
                (int(row["price_cents"]), criteria.price_min_cents, criteria.price_max_cents),
                (int(row["sqft"]), criteria.sqft_min, criteria.sqft_max),
            )
            if any(
                (low is not None and value < low) or (high is not None and value > high)
                for value, low, high in bounds
            ):
                continue
            counts[row["month"]] += 1
    visible = {month: counts[month] for month in request.visible_months}
    assert sum(visible.values()) == 35 and sum(counts.values()) == 63
    assert min(visible.values()) == 2 and max(visible.values()) == 5
    assert visible == {month.month: month.listing_count for month in output.canonical.monthly}

    selections = [event for event in trace if event["event"] == "SELECTION_COMPLETED"]
    assert len(selections) == 2
    assert [event["payload"]["strategy"] for event in selections] == ["indexed", "full_csv"]
    assert all(event["payload"]["selected_required_month_observations"] == 63 for event in selections)
    assert all(not event["payload"]["missing_index_partitions"] for event in selections)
    assert selections[0]["payload"]["selection_sha256"] == selections[1]["payload"]["selection_sha256"]
    refinement = next(event for event in trace if event["event"] == "REFINEMENT_APPLIED")
    assert refinement["payload"]["criteria_hash_before"] == refinement["payload"]["criteria_hash_after"]
    assert refinement["payload"]["strategy_changed"] is True
    assert refinement["payload"]["active_specialists_changed"] is True
    assert refinement["payload"]["after"]["region_purpose"] == "coverage_diagnostic"
    assert refinement["payload"]["after"]["active_specialists"] == ["price", "supply", "region"]
    aggregates = [event for event in trace if event["event"] == "AGGREGATE_COMPLETED"]
    assert len(aggregates) == 2
    assert aggregates[0]["plan_sha256"] != aggregates[1]["plan_sha256"]
    assert aggregates[0]["payload"]["canonical_sha256"] == aggregates[1]["payload"]["canonical_sha256"]
    for role in ("price", "supply"):
        assert (
            aggregates[0]["payload"]["receipt_hashes"][role]
            != aggregates[1]["payload"]["receipt_hashes"][role]
        )
    reviews = [event["payload"]["decision"] for event in trace if event["event"] == "REVIEW_DECIDED"]
    assert [review["decision"] for review in reviews] == ["REFINE", "ACCEPT_LIMITED"]
    assert reviews[0]["signals"] == ["SPARSE_SLICE"]
    assert reviews[0]["requested_action"] == "EXACT_RESCAN_WITH_REGION"
    assert reviews[1]["signals"] == ["CONFIRMED_SPARSE"]
    assert output.quality.status == "limited"
    assert set(output.narrative.caveat_codes) == {"SYNTHETIC_DATA", "SPARSE_SUPPORT", "UNAVAILABLE_LOOKBACK"}
    responses = sorted((run / "model").glob("*.response.json"))
    roles = Counter(
        json.loads(path.with_name(path.name.replace(".response.", ".input.")).read_bytes())["agent"].split(
            "[", 1
        )[0]
        for path in responses
    )
    assert len(responses) == 16 and set(roles) == {
        "orchestrator",
        "price",
        "supply",
        "region",
        "reviewer",
        "composer",
    }
    tools = [event for event in trace if event["event"] == "TOOL_COMPLETED"]
    assert [(event["iteration"], event["actor"]) for event in tools] == [
        (0, "price"),
        (0, "supply"),
        (1, "price"),
        (1, "supply"),
        (1, "region"),
    ]

    replays = [
        json.loads(path.read_bytes())
        for path in sorted((ROOT / "artifacts/rca/MR01-b010-s104729").glob("*/comparison.json"))
    ]
    replay = next(item for item in reversed(replays) if item["capture"] == case.source.run_path)
    assert (
        replay["status"] == "matched" and replay["model_decisions"] == 16 and replay["network_attempts"] == []
    )
    replay_run = ROOT / replay["replay"]
    for live_result in sorted((run / "tools").glob("*/*.result.json")):
        assert json.loads(live_result.read_bytes()) == json.loads(
            (replay_run / live_result.relative_to(run)).read_bytes()
        )
    bound = [
        case_path,
        csv_path,
        Path(__file__).resolve(),
        *sorted(path for path in run.rglob("*") if path.is_file()),
        *sorted(path for path in replay_run.parent.parent.rglob("*") if path.is_file()),
    ]
    write_json(
        packet / "evidence-check.json",
        {
            "status": "verified_named_example",
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "scope": "Report page 4 natural source only; not full campaign reproduction or final PDF QA",
            "capture": case.source.run_path,
            "visible_monthly_counts": visible,
            "visible_total": 35,
            "required_available_total": 63,
            "model_decisions": 16,
            "roles": dict(sorted(roles.items())),
            "source_reused": False,
            "injected_index_omissions": [],
            "replay": replay,
            "source_hashes": {str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes()) for path in bound},
        },
    )
    print(
        "Verified natural source: 35 visible / 63 available required observations; real refinement; five fresh tools; 16 model decisions; strict playback matched with zero network attempts."
    )


if __name__ == "__main__":
    main()
