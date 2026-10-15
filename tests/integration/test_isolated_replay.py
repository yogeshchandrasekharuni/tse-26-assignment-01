"""Actual paired playback must survive interpreter recycling without changing semantics."""

import json
import shutil
import uuid

import pytest

from housing.evaluation.aggregate import case_semantics
from housing.evaluation.models import CaseResult
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT
from housing.reporting.isolated_replay import IsolatedReplayRunner, ReplayLegJob, execute_leg
from housing.workflow.boundary import execution_identity


@pytest.mark.asyncio
async def test_actual_pairs_match_across_spawned_process_recycling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    directory = ROOT / "tmp" / f"isolated-pairs-{uuid.uuid4().hex}"
    reference = ROOT / "artifacts/campaigns/headline-live-v1"
    runner = IsolatedReplayRunner(
        directory, ROOT / "configs/headline-cohort-v1.json", live_reference=reference, batch_size=3
    )
    process_pairs: list[set[int]] = []
    try:
        for base_id, seed in (("b001", 104729), ("b003", 155921)):
            spec = next(case for case in runner.cohort.cases if case.mr == "MR01" and case.base_id == base_id)
            name = f"MR01-{base_id}-s{seed}"
            live = CaseResult.model_validate_json((reference / "cases" / name / "result.json").read_bytes())
            replay = await runner.case(spec, seed, directory / "cases" / name / "attempt-001", live)
            assert case_semantics(replay) == case_semantics(live)
            pids = set()
            for leg in (replay.source, replay.followup):
                run = ROOT / leg.run_path
                terminal = json.loads((run / "terminal.json").read_bytes())
                assert terminal["network_attempts"] == [] and terminal["model_decisions"] > 0
                evidence = json.loads((run.parent.parent / "execution-process.json").read_bytes())
                pids.add(evidence["worker_pid"])
            process_pairs.append(pids)
        assert len(process_pairs[0]) == 1 and len(process_pairs[1]) == 2
        assert process_pairs[0] < process_pairs[1]
    finally:
        runner.close()
        shutil.rmtree(directory, ignore_errors=True)


def test_process_rejects_a_changed_parent_boundary_before_any_execution() -> None:
    directory = ROOT / "tmp" / f"isolated-reject-{uuid.uuid4().hex}"
    runner = IsolatedReplayRunner(
        directory,
        ROOT / "configs/headline-cohort-v1.json",
        live_reference=ROOT / "artifacts/campaigns/headline-live-v1",
    )
    try:
        spec = runner.cohort.cases[0]
        request = updated_request(spec.source_request, seed=104729)
        changed, followup = transform(runner.snapshot, request, spec.recipe, runner.dataset_manifest)
        live = CaseResult.model_validate_json(
            (ROOT / "artifacts/campaigns/headline-live-v1/cases/MR01-b001-s104729/result.json").read_bytes()
        )
        job = ReplayLegJob(
            case=spec,
            seed=104729,
            leg="followup",
            directory=str(directory.relative_to(ROOT)),
            cohort_path="configs/headline-cohort-v1.json",
            live_reference="artifacts/campaigns/headline-live-v1",
            location=str((directory / "never-created/followup").relative_to(ROOT)),
            capture=live.followup.run_path,
            expected_identity=execution_identity(followup, changed).model_copy(
                update={"model_digest": "0" * 64}
            ),
        )
        with pytest.raises(ValueError, match="exact parent boundary"):
            execute_leg(job.model_dump_json())
        assert not directory.exists()
    finally:
        runner.close()
