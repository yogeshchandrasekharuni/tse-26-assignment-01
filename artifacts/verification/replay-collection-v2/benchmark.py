"""Auxiliary resource experiment: identical real failed playback, explicit GC frequency only."""

import asyncio
import gc
import json
import resource
import sys
import time
from pathlib import Path
from unittest.mock import patch

from housing.data.models import DatasetManifest
from housing.evaluation.models import Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes, write_json
from housing.reporting.replay_metadata import ReplayMetadataRunner

period = int(sys.argv[1])
assert period in (1, 16)
packet = Path(__file__).resolve().parent
capture = ROOT / (
    "artifacts/campaigns/headline-live-v1/cases/MR01-b003-s155921/attempt-001/"
    "followup/runs/20261002T033100Z-17d9d8cdf3"
)
cohort_path = ROOT / "configs/headline-cohort-v1.json"
cohort = Cohort.model_validate_json(cohort_path.read_bytes())
spec = next(case for case in cohort.cases if case.mr == "MR01" and case.base_id == "b003")
runner = ReplayMetadataRunner(ROOT / "tmp" / f"gc-benchmark-{period}", cohort_path, mode="replay")
snapshot, request = transform(
    runner.snapshot,
    updated_request(spec.source_request, seed=155921),
    spec.recipe,
    DatasetManifest.model_validate_json((ROOT / "data/manifests/dallas-synth-v1.json").read_bytes()),
)
destination = ROOT / "tmp" / f"gc-benchmark-{period}"
assert not destination.exists()
real_collect = gc.collect
requests = collections = collection_cpu_ns = 0


def measured_collect(generation: int = 2) -> int:
    global requests, collections, collection_cpu_ns
    requests += 1
    if requests % period:
        return 0
    start = time.process_time_ns()
    result = real_collect(generation)
    collection_cpu_ns += time.process_time_ns() - start
    collections += 1
    return result


async def run() -> None:
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    with patch("housing.reporting.replay_metadata.gc.collect", measured_collect):
        for index in range(16):
            outcome, output = await runner.leg(request, snapshot, destination / f"leg-{index:02}", capture=capture)
            assert output is None and outcome.error_code == "AGENT_POLICY_ERROR"
            assert outcome.error_stage == "SCANNING" and outcome.effective_seed == 155921
            terminal = json.loads((ROOT / outcome.run_path / "terminal.json").read_bytes())
            assert terminal["model_decisions"] == 4 and terminal["network_attempts"] == []
    assert requests == 16
    write_json(
        packet / f"period-{period}.json",
        {
            "status": "verified_auxiliary_resource_experiment",
            "interpretation": "Sixteen repeated actual offline failures; not new empirical samples, not a fresh model run, and not a guarantee for all workloads. Different GC frequency is injected only in this isolated benchmark process.",
            "period": period,
            "physical_playback_legs": 16,
            "explicit_collection_requests": requests,
            "collections_performed": collections,
            "wall_ns": time.perf_counter_ns() - wall,
            "process_cpu_ns": time.process_time_ns() - cpu,
            "collection_cpu_ns": collection_cpu_ns,
            "maxrss_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "raw_outputs": str(destination.relative_to(ROOT)),
            "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "adapter_sha256": sha256_bytes((ROOT / "src/housing/reporting/replay_metadata.py").read_bytes()),
        },
    )
    print(f"period{period}:16 exact failure playbacks verified; collections{collections}", flush=True)


asyncio.run(run())
