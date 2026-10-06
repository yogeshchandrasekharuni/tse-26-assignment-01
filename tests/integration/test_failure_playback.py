"""A natural eligible model failure must reproduce as failure, without a saved answer."""

import json
import shutil
from pathlib import Path
from typing import Literal

import pytest

from housing.contracts.errors import HousingError
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import Cohort, MRId
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT
from housing.workflow.service import run_analysis


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mr_id", "base_id", "run_relative", "invalid_role", "decisions", "expected_tools"),
    [
        (
            "MR01",
            "b003",
            (
                "artifacts/campaigns/headline-live-v1/cases/MR01-b003-s155921/attempt-001/"
                "followup/runs/20261002T033100Z-17d9d8cdf3"
            ),
            "price",
            4,
            (),
        ),
        (
            "MR02",
            "b013",
            (
                "artifacts/campaigns/headline-live-v1/cases/MR02-b013-s155921/attempt-001/"
                "followup/runs/20261004T114202Z-39a221977d"
            ),
            "supply",
            5,
            ("price",),
        ),
    ],
    ids=["price_before_tools", "supply_after_price"],
)
async def test_natural_role_purpose_failure_replays_exactly_without_final_output(
    tmp_path: Path,
    mr_id: MRId,
    base_id: str,
    run_relative: str,
    invalid_role: Literal["price", "supply"],
    decisions: int,
    expected_tools: tuple[str, ...],
) -> None:
    capture = ROOT / run_relative
    minimal_capture = tmp_path / "minimal-capture"
    minimal_capture.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(capture / name, minimal_capture / name)
    shutil.copytree(capture / "cassettes", minimal_capture / "cassettes")
    assert {path.name for path in minimal_capture.iterdir()} == {
        "run-manifest.json",
        "terminal.json",
        "cassettes",
    }
    cohort = Cohort.model_validate_json((ROOT / "configs/headline-cohort-v1.json").read_bytes())
    spec = next(case for case in cohort.cases if case.mr == mr_id and case.base_id == base_id)
    snapshot, request = transform(
        load_snapshot(CSV_PATH, MANIFEST_PATH),
        updated_request(spec.source_request, seed=155921),
        spec.recipe,
        DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes()),
    )
    with pytest.raises(HousingError, match="Schema repair must finish") as failure:
        await run_analysis(
            request, snapshot, mode="replay", capture=minimal_capture, artifact_root=tmp_path / "replay"
        )
    assert failure.value.code == "AGENT_POLICY_ERROR"
    assert failure.value.stage == "SCANNING"
    run = next((tmp_path / "replay").iterdir())
    terminal = json.loads((run / "terminal.json").read_bytes())
    assert terminal["status"] == "failed"
    assert terminal["model_decisions"] == decisions
    assert terminal["network_attempts"] == []
    assert not (run / "output.json").exists()
    events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    invalid = next(
        event
        for event in events
        if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False
    )
    assert invalid["actor"] == invalid_role
    assert json.loads(invalid["payload"]["raw"])["purpose"] == "public_comparison"
    tools = [event for event in events if event["event"] == "TOOL_COMPLETED"]
    assert tuple(event["actor"] for event in tools) == expected_tools
    for tool in tools:
        assert tool["sequence"] < invalid["sequence"]
        role = tool["actor"]
        assert (run / "tools" / "iteration-0" / f"{role}_stats.result.json").is_file()
        assert (run / "tools" / "iteration-0" / f"{role}_stats.receipt.json").is_file()
    assert not any(event["event"] == "AGGREGATE_COMPLETED" for event in events)


@pytest.mark.asyncio
async def test_natural_schema_echo_exhausts_repair_after_recomputed_tools(tmp_path: Path) -> None:
    capture = ROOT / (
        "artifacts/campaigns/headline-live-v1/cases/MR01-b013-s104729/attempt-001/"
        "followup/runs/20261002T212554Z-5422070b41"
    )
    minimal = tmp_path / "minimal-capture"
    minimal.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(capture / name, minimal / name)
    shutil.copytree(capture / "cassettes", minimal / "cassettes")
    assert {path.name for path in minimal.iterdir()} == {"run-manifest.json", "terminal.json", "cassettes"}
    cohort = Cohort.model_validate_json((ROOT / "configs/headline-cohort-v1.json").read_bytes())
    spec = next(case for case in cohort.cases if case.mr == "MR01" and case.base_id == "b013")
    snapshot, request = transform(
        load_snapshot(CSV_PATH, MANIFEST_PATH),
        updated_request(spec.source_request, seed=104729),
        spec.recipe,
        DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes()),
    )
    with pytest.raises(HousingError, match="one explicit schema repair was exhausted") as failure:
        await run_analysis(
            request, snapshot, mode="replay", capture=minimal, artifact_root=tmp_path / "replay"
        )
    assert failure.value.code == "AGENT_OUTPUT_INVALID"
    assert failure.value.stage == "REVIEW_REQUIRED"
    run = next((tmp_path / "replay").iterdir())
    terminal = json.loads((run / "terminal.json").read_bytes())
    assert terminal["status"] == "failed"
    assert terminal["model_decisions"] == 10
    assert terminal["network_attempts"] == []
    assert not (run / "output.json").exists()
    events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    tools = [event for event in events if event["event"] == "TOOL_COMPLETED"]
    assert len(tools) == 3 and {event["actor"] for event in tools} == {"price", "supply", "region"}
    for role in ("price", "supply", "region"):
        assert (run / "tools" / "iteration-0" / f"{role}_stats.result.json").is_file()
    invalid = [
        event
        for event in events
        if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False
    ]
    assert len(invalid) == 2 and all(event["actor"] == "reviewer" for event in invalid)
    assert invalid[0]["payload"]["raw"] == invalid[1]["payload"]["raw"]
    assert json.loads(invalid[0]["payload"]["raw"])["properties"]["role"]["const"] == "reviewer"
    assert max(event["sequence"] for event in tools) < invalid[0]["sequence"]
    repairs = [event for event in events if event["event"] == "AGENT_REPAIR"]
    assert len(repairs) == 1 and repairs[0]["actor"] == "reviewer"
    assert not any(event["event"] == "REVIEW_DECIDED" for event in events)


@pytest.mark.asyncio
async def test_failed_refinement_never_publishes_the_initial_provisional_aggregate(tmp_path: Path) -> None:
    capture = ROOT / (
        "artifacts/campaigns/headline-live-v1/cases/MR05-b010-s104729/attempt-001/"
        "followup/runs/20261006T173448Z-9bb7b33a7f"
    )
    minimal = tmp_path / "minimal-capture"
    minimal.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(capture / name, minimal / name)
    shutil.copytree(capture / "cassettes", minimal / "cassettes")
    assert {path.name for path in minimal.iterdir()} == {"run-manifest.json", "terminal.json", "cassettes"}
    cohort = Cohort.model_validate_json((ROOT / "configs/headline-cohort-v1.json").read_bytes())
    spec = next(case for case in cohort.cases if case.mr == "MR05" and case.base_id == "b010")
    snapshot, request = transform(
        load_snapshot(CSV_PATH, MANIFEST_PATH),
        updated_request(spec.source_request, seed=104729),
        spec.recipe,
        DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes()),
    )
    with pytest.raises(HousingError, match="Schema repair must finish") as failure:
        await run_analysis(
            request, snapshot, mode="replay", capture=minimal, artifact_root=tmp_path / "replay"
        )
    assert failure.value.code == "AGENT_POLICY_ERROR"
    assert failure.value.stage == "SCANNING"
    run = next((tmp_path / "replay").iterdir())
    terminal = json.loads((run / "terminal.json").read_bytes())
    assert terminal["status"] == "failed"
    assert terminal["model_decisions"] == 10
    assert terminal["network_attempts"] == []
    assert not (run / "output.json").exists()
    events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    refinements = [event for event in events if event["event"] == "REFINEMENT_APPLIED"]
    assert len(refinements) == 1
    refinement = refinements[0]
    before, after = (refinement["payload"][name] for name in ("before", "after"))
    assert before["version"] == 0 and after["version"] == 1
    assert before["scan_strategy"] == "indexed" and after["scan_strategy"] == "full_csv"
    assert before["active_specialists"] == ["price", "supply"]
    assert after["active_specialists"] == ["price", "supply", "region"]
    assert after["region_purpose"] == "coverage_diagnostic"
    assert refinement["payload"]["refinements_used"] == 1
    assert refinement["payload"]["criteria_hash_before"] == refinement["payload"]["criteria_hash_after"]
    assert before["canonical_query_sha256"] == after["canonical_query_sha256"]
    tools = [event for event in events if event["event"] == "TOOL_COMPLETED"]
    assert [(event["actor"], event["iteration"]) for event in tools] == [("price", 0), ("supply", 0)]
    for role in ("price", "supply"):
        assert (run / "tools" / "iteration-0" / f"{role}_stats.result.json").is_file()
        assert (run / "tools" / "iteration-0" / f"{role}_stats.receipt.json").is_file()
    aggregates = [event for event in events if event["event"] == "AGGREGATE_COMPLETED"]
    assert len(aggregates) == 1 and aggregates[0]["sequence"] < refinement["sequence"]
    assert aggregates[0]["iteration"] == 0
    invalid = next(
        event
        for event in events
        if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False
    )
    assert invalid["actor"] == "price" and invalid["iteration"] == after["version"]
    assert invalid["sequence"] > refinement["sequence"]
    assert json.loads(invalid["payload"]["raw"])["purpose"] == "coverage_diagnostic"
    assert not (run / "tools" / "iteration-1").exists()
