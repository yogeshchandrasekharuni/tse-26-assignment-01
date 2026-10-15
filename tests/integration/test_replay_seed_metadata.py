"""Regress the failed-leg seed mismatch found only by the full clean-checkout run."""

import json
import shutil
from pathlib import Path

import pytest

from housing.data.models import DatasetManifest
from housing.evaluation.models import Cohort, LegOutcome
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes
from housing.reporting.replay_metadata import ReplayMetadataRunner, attribute_failed_seed

CAPTURE = ROOT / (
    "artifacts/campaigns/headline-live-v1/cases/MR01-b003-s155921/attempt-001/"
    "followup/runs/20261002T033100Z-17d9d8cdf3"
)


@pytest.mark.asyncio
async def test_failed_playback_attributes_the_exact_historical_seed_and_preserves_raw_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    minimal = tmp_path / "capture"
    minimal.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(CAPTURE / name, minimal / name)
    shutil.copytree(CAPTURE / "cassettes", minimal / "cassettes")
    cohort_path = ROOT / "configs/headline-cohort-v1.json"
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    spec = next(case for case in cohort.cases if case.mr == "MR01" and case.base_id == "b003")
    runner = ReplayMetadataRunner(tmp_path / "campaign", cohort_path, mode="replay")
    snapshot, request = transform(
        runner.snapshot,
        updated_request(spec.source_request, seed=155921),
        spec.recipe,
        DatasetManifest.model_validate_json((ROOT / "data/manifests/dallas-synth-v1.json").read_bytes()),
    )
    monkeypatch.setattr("housing.evaluation.runner.ROOT", tmp_path)
    monkeypatch.setattr("housing.reporting.replay_metadata.ROOT", tmp_path)
    location = tmp_path / "failed"
    outcome, output = await runner.leg(request, snapshot, location, capture=minimal)
    assert output is None
    assert outcome.status == "failed" and outcome.error_code == "AGENT_POLICY_ERROR"
    assert outcome.error_stage == "SCANNING" and outcome.effective_seed == 155921
    original_record = location / "record.before-seed-attribution.json"
    uncorrected = LegOutcome.model_validate_json(original_record.read_bytes())
    assert uncorrected.effective_seed is None
    assert outcome.model_dump(exclude={"effective_seed"}) == uncorrected.model_dump(
        exclude={"effective_seed"}
    )
    provenance = json.loads((location / "seed-attribution.json").read_bytes())
    assert provenance["captured_seed"] == 155921 and provenance["decisions_replayed"] == 4
    assert provenance["original_leg_record_sha256"] == sha256_bytes(original_record.read_bytes())
    run = tmp_path / outcome.run_path
    terminal_path = run / "terminal.json"
    terminal_bytes = terminal_path.read_bytes()
    terminal = json.loads(terminal_bytes)
    assert terminal["network_attempts"] == [] and terminal["model_decisions"] == 4
    assert not (run / "output.json").exists() and not (run / "cassettes").exists()

    # Explicit tampering controls are auxiliary; they must never acquire a seed
    # merely from a matching requested number or a partial sequence.
    (location / "record.json").write_bytes(original_record.read_bytes())
    for key, value in (("model_decisions", 3), ("network_attempts", ["blocked connect"])):
        terminal_path.write_text(json.dumps({**terminal, key: value}))
        with pytest.raises(ValueError, match="complete exact captured-seed"):
            attribute_failed_seed(uncorrected, request, snapshot, minimal)
    terminal_path.write_bytes(terminal_bytes)
    changed_request = request.model_copy(update={"seed": 104729})
    with pytest.raises(ValueError, match="complete exact captured-seed"):
        attribute_failed_seed(uncorrected, changed_request, snapshot, minimal)

    miss, miss_output = await runner.leg(changed_request, snapshot, tmp_path / "miss", capture=minimal)
    assert miss_output is None and miss.error_code == "REPLAY_MISS"
    assert miss.effective_seed is None
    assert not (tmp_path / "miss/seed-attribution.json").exists()


@pytest.mark.asyncio
async def test_replay_metadata_adapter_refuses_live_execution(tmp_path: Path) -> None:
    runner = ReplayMetadataRunner(tmp_path, ROOT / "configs/headline-cohort-v1.json", mode="live")
    spec = runner.cohort.cases[0]
    with pytest.raises(ValueError, match="cannot execute live"):
        await runner.leg(spec.source_request, runner.snapshot, tmp_path / "never-created", capture=None)
    assert not (tmp_path / "never-created").exists()
