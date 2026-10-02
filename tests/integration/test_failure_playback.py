"""A natural eligible model failure must reproduce as failure, without a saved answer."""

import json
import shutil
from pathlib import Path

import pytest

from housing.contracts.errors import HousingError
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT
from housing.workflow.service import run_analysis


@pytest.mark.asyncio
async def test_natural_role_purpose_failure_replays_exactly_without_final_output(tmp_path: Path) -> None:
    capture = ROOT / (
        "artifacts/campaigns/headline-live-v1/cases/MR01-b003-s155921/attempt-001/"
        "followup/runs/20261002T033100Z-17d9d8cdf3"
    )
    minimal_capture = tmp_path / "minimal-capture"
    minimal_capture.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(capture / name, minimal_capture / name)
    shutil.copytree(capture / "cassettes", minimal_capture / "cassettes")
    cohort = Cohort.model_validate_json((ROOT / "configs/headline-cohort-v1.json").read_bytes())
    spec = next(case for case in cohort.cases if case.mr == "MR01" and case.base_id == "b003")
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
    assert terminal["model_decisions"] == 4
    assert terminal["network_attempts"] == []
    assert not (run / "output.json").exists()
    events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    invalid = next(
        event
        for event in events
        if event["event"] == "AGENT_DECISION" and event["payload"].get("valid") is False
    )
    assert invalid["actor"] == "price"
    assert json.loads(invalid["payload"]["raw"])["purpose"] == "public_comparison"
