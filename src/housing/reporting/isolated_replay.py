"""Bound replay interpreter lifetimes while retaining the frozen per-analysis execution."""

import asyncio
import multiprocessing
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import cache
from pathlib import Path
from typing import Literal

from housing.contracts.common import FrozenModel, PositiveInt, Seed, Sha256
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.store import Snapshot
from housing.evaluation.models import CaseResult, CaseSpec, LegOutcome
from housing.evaluation.runner import CONTRACT_FAULTS, CampaignRunner
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.reporting.replay_metadata import attribute_failed_seed
from housing.workflow.boundary import ExecutionIdentity, execution_identity

REVISION = "bounded-process-playback-2"


class ReplayLegJob(FrozenModel):
    case: CaseSpec
    seed: Seed
    leg: Literal["source", "followup"]
    directory: str
    cohort_path: str
    live_reference: str
    location: str
    capture: str
    expected_identity: ExecutionIdentity


class ReplayLegResult(FrozenModel):
    job_sha256: Sha256
    worker_pid: PositiveInt
    outcome: LegOutcome
    output: AnalysisOutput | None


def local_path(value: str) -> Path:
    path = Path(value)
    resolved = (ROOT / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(ROOT):
        raise ValueError("Replay process paths must remain inside this checkout")
    return resolved


@cache
def worker_runner(directory: str, cohort_path: str, live_reference: str) -> CampaignRunner:
    return CampaignRunner(
        local_path(directory),
        local_path(cohort_path),
        mode="replay",
        live_reference=local_path(live_reference),
    )


def execute_leg(serialized_job: str) -> str:
    """Execute real current playback; IPC returns only its newly computed typed result."""
    job = ReplayLegJob.model_validate_json(serialized_job)
    runner = worker_runner(job.directory, job.cohort_path, job.live_reference)
    snapshot = runner.snapshot
    request = updated_request(job.case.source_request, seed=job.seed)
    if job.leg == "followup":
        snapshot, request = transform(snapshot, request, job.case.recipe, runner.dataset_manifest)
    if execution_identity(request, snapshot) != job.expected_identity:
        raise ValueError("Replay process materialization differs from the exact parent boundary")
    location, capture = local_path(job.location), local_path(job.capture)
    if not location.is_relative_to(runner.directory):
        raise ValueError("Replay process destination belongs to another reproduction")
    outcome, output = asyncio.run(runner.leg(request, snapshot, location, capture=capture))
    if outcome.status == "failed" and outcome.error_code in CONTRACT_FAULTS:
        attributed, provenance = attribute_failed_seed(outcome, request, snapshot, capture)
        with (location / "record.before-seed-attribution.json").open("xb") as stream:
            stream.write((location / "record.json").read_bytes())
        write_json(location / "seed-attribution.json", provenance)
        write_json(location / "record.json", attributed)
        outcome = attributed
    result = ReplayLegResult(
        job_sha256=semantic_hash(job), worker_pid=os.getpid(), outcome=outcome, output=output
    )
    write_json(
        location / "execution-process.json",
        {
            "revision": REVISION,
            "worker_pid": result.worker_pid,
            "job_sha256": result.job_sha256,
            "boundary_sha256": semantic_hash(job.expected_identity),
            "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "interpretation": "Actual current service executed in an isolated replay process; returned output is fresh computation, not a loaded live final answer",
        },
    )
    return result.model_dump_json()


class IsolatedReplayRunner(CampaignRunner):
    """A sequential harness; the agent topology inside each analysis is unchanged."""

    def __init__(self, directory: Path, cohort_path: Path, *, live_reference: Path, batch_size: int = 16):
        if not 1 <= batch_size <= 16:
            raise ValueError("Replay process lifetime must be one to sixteen physical analyses")
        super().__init__(directory, cohort_path, mode="replay", live_reference=live_reference)
        self.batch_size = batch_size
        self.active_spec: CaseSpec | None = None
        self.executor = ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn"), max_tasks_per_child=batch_size
        )

    def manifest(self) -> dict[str, object]:
        return {
            **super().manifest(),
            "replay_resource_adapter": {
                "revision": REVISION,
                "max_physical_analyses_per_process": self.batch_size,
                "processes_at_once": 1,
                "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
                "seed_attribution_source_sha256": sha256_bytes(
                    (ROOT / "src/housing/reporting/replay_metadata.py").read_bytes()
                ),
            },
            "actual_delivery_driver": [sys.executable, *sys.argv],
        }

    async def case(
        self, spec: CaseSpec, seed: int, attempt: Path, reference: CaseResult | None
    ) -> CaseResult:
        self.active_spec = spec
        try:
            return await super().case(spec, seed, attempt, reference)
        finally:
            self.active_spec = None

    async def leg(
        self, request: AnalysisRequest, snapshot: Snapshot, location: Path, *, capture: Path | None
    ) -> tuple[LegOutcome, AnalysisOutput | None]:
        if self.active_spec is None or capture is None or self.live_reference is None:
            raise ValueError("Isolated playback needs its current frozen case and actual live capture")
        label = location.name
        if label not in {"source", "followup"}:
            raise ValueError("Unknown logical playback leg")
        job = ReplayLegJob(
            case=self.active_spec,
            seed=request.seed,
            leg="source" if label == "source" else "followup",
            directory=str(self.directory.relative_to(ROOT)),
            cohort_path=str(self.cohort_path.relative_to(ROOT)),
            live_reference=str(self.live_reference.relative_to(ROOT)),
            location=str(location.relative_to(ROOT)),
            capture=str(capture.relative_to(ROOT)),
            expected_identity=execution_identity(request, snapshot),
        )
        serialized = await asyncio.get_running_loop().run_in_executor(
            self.executor, execute_leg, job.model_dump_json()
        )
        result = ReplayLegResult.model_validate_json(serialized)
        outcome, output = result.outcome, result.output
        if (
            result.job_sha256 != semantic_hash(job)
            or outcome.execution_key != semantic_hash(job.expected_identity)
            or outcome.request_sha256 != semantic_hash(request)
            or outcome.view_sha256 != snapshot.view_sha256
            or outcome.capture_path != job.capture
            or (output is not None and outcome.output_sha256 != semantic_hash(output))
            or (outcome.status == "completed") != (output is not None)
        ):
            raise ValueError("Replay process response differs from its exact executed job")
        return outcome, output

    def close(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=False)
