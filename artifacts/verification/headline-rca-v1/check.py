"""Review the fixed top-three representatives against raw data and minimal actual playback."""

import asyncio
import csv
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from housing.contracts.decisions import PriceDecision, SupplyDecision
from housing.contracts.errors import HousingError
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import CaseResult, Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes, write_json
from housing.replay.capture import load_cassettes
from housing.workflow.service import run_analysis

PACKET = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "artifacts/campaigns/headline-live-v1"


def months(end: str) -> tuple[str, ...]:
    year, month = map(int, end.split("-"))
    last = year * 12 + month - 1
    return tuple(f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(last - 11, last + 1))


def selected(rows: list[dict[str, str]], request: AnalysisRequest) -> list[dict[str, str]]:
    """Simple raw selector; no production selector, statistical tool or comparator."""
    c = request.criteria
    visible = set(months(request.window_end))
    return [
        row
        for row in rows
        if row["month"] in visible
        and row["zip"] in c.zips
        and row["property_type"] in c.property_types
        and c.bedrooms_min <= int(row["bedrooms"]) <= c.bedrooms_max
        and (c.price_min_cents is None or int(row["price_cents"]) >= c.price_min_cents)
        and (c.price_max_cents is None or int(row["price_cents"]) <= c.price_max_cents)
        and (c.sqft_min is None or int(row["sqft"]) >= c.sqft_min)
        and (c.sqft_max is None or int(row["sqft"]) <= c.sqft_max)
    ]


def signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        row[key] for key in ("listing_id", "month", "zip", "property_type", "bedrooms", "sqft", "price_cents")
    )


def response_text(run: Path, sequence: int) -> str:
    body = json.loads((run / "model" / f"{sequence:03d}.response.json").read_bytes())
    return "\n".join(block["text"] for block in body["content"] if block["type"] == "text")


async def main() -> None:
    candidates_path = ROOT / "reports/data/headline-live-v1-diagnosis-candidates.json"
    candidates = json.loads(candidates_path.read_bytes())
    assert candidates["status"] == "requires_review"
    assert candidates["ranked_relations"][:3] == ["MR03", "MR05", "MR07"]
    assert candidates["headline_sha256"] == sha256_bytes((CAMPAIGN / "headline.json").read_bytes())
    cohort_path = ROOT / "configs/headline-cohort-v1.json"
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    manifest = DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
    with CSV_PATH.open(newline="") as stream:
        raw = list(csv.DictReader(stream))
    assert len(raw) == 34560 and len({row["record_id"] for row in raw}) == 34560
    expected = [
        ("MR03-b001-s104729", "followup"),
        ("MR05-b001-s104729", "source"),
        ("MR07-b001-s130363", "followup"),
    ]
    findings = []
    hashes = {
        str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes())
        for path in (
            Path(__file__),
            CSV_PATH,
            MANIFEST_PATH,
            cohort_path,
            candidates_path,
            ROOT / "src/housing/contracts/decisions.py",
            ROOT / "src/housing/workflow/controller.py",
        )
    }
    for chosen, (name, label) in zip(candidates["selected"], expected, strict=True):
        case_path = CAMPAIGN / "cases" / name / "result.json"
        case = CaseResult.model_validate_json(case_path.read_bytes())
        assert case == CaseResult.model_validate_json(json.dumps(chosen["representative"]))
        spec = next(spec for spec in cohort.cases if spec.mr == case.mr_id and spec.base_id == case.base_id)
        request = updated_request(spec.source_request, seed=case.seed)
        changed, followup = transform(snapshot, request, spec.recipe, manifest)
        transformed = [{key: str(value) for key, value in row.model_dump().items()} for row in changed.rows]
        source_rows, followup_rows = selected(raw, request), selected(transformed, followup)
        source_ids = {row["record_id"] for row in source_rows}
        followup_ids = {row["record_id"] for row in followup_rows}
        witness: dict[str, object] = {
            "source_selected": len(source_rows),
            "followup_selected": len(followup_rows),
        }
        assert source_rows and followup_rows
        if case.mr_id == "MR03":
            base_multiset = Counter(signature(row) for row in raw)
            assert len(transformed) == 2 * len(raw)
            assert len({row["record_id"] for row in transformed}) == len(transformed)
            assert Counter(signature(row) for row in transformed) == Counter(
                {key: 2 * value for key, value in base_multiset.items()}
            )
            original_by_id = {row["record_id"]: row for row in transformed}
            assert all(original_by_id[row["record_id"]] == row for row in raw)
            assert len(followup_rows) == 2 * len(source_rows)
            witness.update(
                {
                    "raw_rows": len(raw),
                    "transformed_rows": len(transformed),
                    "identity_safe_exact_twofold_multiset": True,
                }
            )
        elif case.mr_id == "MR05":
            assert transformed == raw
            assert source_ids < followup_ids
            assert request.criteria.model_dump(
                exclude={"price_min_cents", "price_max_cents"}
            ) == followup.criteria.model_dump(exclude={"price_min_cents", "price_max_cents"})
            witness.update(
                {
                    "added_selected_observations": len(followup_ids - source_ids),
                    "data_unchanged": True,
                    "failed_leg_precedes_transformation": True,
                }
            )
        else:
            assert case.mr_id == "MR07" and transformed == raw
            before, after = months(request.window_end), months(followup.window_end)
            assert before[1:] == after[:-1] and len(set(before) & set(after)) == 11
            assert request.model_dump(exclude={"window_end"}) == followup.model_dump(exclude={"window_end"})
            for month in before[1:]:
                assert Counter(signature(row) for row in source_rows if row["month"] == month) == Counter(
                    signature(row) for row in followup_rows if row["month"] == month
                )
            assert source_ids != followup_ids
            witness.update(
                {
                    "overlap_months": before[1:],
                    "same_raw_multiset_in_each_overlap": True,
                    "leaving_records": len(source_ids - followup_ids),
                    "entering_records": len(followup_ids - source_ids),
                }
            )

        leg = case.source if label == "source" else case.followup
        run = ROOT / leg.run_path
        packets = load_cassettes(run)
        assert len(packets) == 4
        delegation = packets[1].response["tool_calls"]
        messages = {
            delegation[key]["params"]["name"]: delegation[key]["params"]["arguments"]["message"]
            for key in packets[1].response_tool_call_order
        }
        assert set(messages) == {"agent__price", "agent__supply", "agent__region"}
        assert "purpose public_comparison" in messages["agent__price"]
        price_raw, supply_raw = response_text(run, 2), response_text(run, 3)
        try:
            PriceDecision.model_validate_json(price_raw)
        except ValidationError as error:
            validation_errors = error.errors(include_url=False, include_input=False)
        else:
            raise AssertionError("The chosen empirical Price intent unexpectedly validates")
        assert len(validation_errors) == 1 and validation_errors[0]["loc"] == ("purpose",)
        assert validation_errors[0]["type"] == "literal_error"
        supply = SupplyDecision.model_validate_json(supply_raw)
        assert supply.purpose == "statistics"
        supply_input = json.loads((run / "model/003.input.json").read_bytes())
        assert supply_input["context"]["schema_repair"]["role"] == "price"
        events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
        assert [event["event"] for event in events][-3:] == ["AGENT_DECISION", "AGENT_REPAIR", "RUN_FAILED"]
        assert not any(
            event["event"] in {"TOOL_COMPLETED", "AGGREGATE_COMPLETED", "RUN_COMPLETED"} for event in events
        )
        control = {**json.loads(price_raw), "purpose": "statistics"}
        PriceDecision.model_validate(control)

        minimal = PACKET / "minimal-captures" / name
        minimal.mkdir(parents=True, exist_ok=False)
        for filename in ("run-manifest.json", "terminal.json"):
            shutil.copyfile(run / filename, minimal / filename)
        shutil.copytree(run / "cassettes", minimal / "cassettes")
        assert {path.name for path in minimal.iterdir()} == {
            "run-manifest.json",
            "terminal.json",
            "cassettes",
        }
        destination = PACKET / "minimal-playback" / name
        observed = None
        try:
            await run_analysis(
                request if label == "source" else followup,
                snapshot if label == "source" else changed,
                mode="replay",
                capture=minimal,
                artifact_root=destination,
            )
        except HousingError as error:
            observed = error
        assert observed is not None and observed.code == "AGENT_POLICY_ERROR" and observed.stage == "SCANNING"
        replay = next(destination.iterdir())
        terminal = json.loads((replay / "terminal.json").read_bytes())
        assert terminal["model_decisions"] == 4 and terminal["network_attempts"] == []
        assert terminal["status"] == "failed" and not (replay / "output.json").exists()
        finding = {
            "case": name,
            "leg": label,
            "source_reused_from": case.source_reused_from,
            "run_path": leg.run_path,
            "raw_witness": witness,
            "empirical_parent_messages": messages,
            "empirical_price_response": json.loads(price_raw),
            "price_schema_errors": validation_errors,
            "empirical_supply_response": supply.model_dump(mode="json"),
            "pending_repair_role_in_supply_context": "price",
            "observed_guard": observed.message,
            "minimal_replay": str(replay.relative_to(ROOT)),
            "model_decisions": 4,
            "network_attempts": [],
            "numeric_comparison": "unavailable because an eligible leg has no final output",
            "auxiliary_schema_control": {
                "interpretation": "Constructed Price intent with only purpose corrected; not a new model response, deployed fix or empirical rerun",
                "decision": control,
            },
        }
        findings.append(finding)
        write_json(PACKET / f"{name}-boundary.json", finding)
        for path in [case_path, *sorted(run.rglob("*")), *sorted(replay.rglob("*"))]:
            if path.is_file():
                hashes[str(path.relative_to(ROOT))] = sha256_bytes(path.read_bytes())
        print(
            f"Reviewed {name}/{label}: raw witness verified, four-decision cassette-only failure reproduced, zero network.",
            flush=True,
        )
    write_json(
        PACKET / "review.json",
        {
            "status": "verified_fixed_top_three_representatives",
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "campaign_id": CAMPAIGN.name,
            "headline_sha256": candidates["headline_sha256"],
            "ranked_relations": candidates["ranked_relations"],
            "selected": findings,
            "common_mechanism": "Regional purpose propagated to Price; valid queued Supply reply rejected while Price repair is pending",
            "interpretation": "Three ranked relations share one demonstrated representative mechanism, not three independent bugs or evidence that these transformations caused it. Other natural mechanisms remain separately documented.",
            "source_hashes": hashes,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
