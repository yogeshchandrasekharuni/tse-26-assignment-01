"""Versioned replay-only attribution; preserve the frozen live runner and every decision."""

import gc
from pathlib import Path
from typing import Literal

from housing.contracts.common import FrozenModel, NonnegativeInt, Seed, Sha256
from housing.contracts.errors import ErrorCode
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.store import Snapshot
from housing.evaluation.models import LegOutcome
from housing.evaluation.runner import CONTRACT_FAULTS, CampaignRunner
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.replay.capture import load_cassettes
from housing.workflow.boundary import RunManifest, execution_identity

REVISION: Literal["replay-failed-seed-attribution-1"] = "replay-failed-seed-attribution-1"


class FailureTerminal(FrozenModel):
    status: Literal["failed"]
    code: ErrorCode
    stage: str
    model_decisions: NonnegativeInt
    network_attempts: tuple[str, ...]
    cassette_hashes: dict[str, Sha256]


class SeedAttribution(FrozenModel):
    schema_version: Literal["replay-failed-seed-attribution-1"]
    interpretation: str
    captured_seed: Seed
    decisions_replayed: NonnegativeInt
    capture_path: str
    live_manifest_sha256: Sha256
    replay_manifest_sha256: Sha256
    replay_terminal_sha256: Sha256
    original_leg_record_sha256: Sha256


def attribute_failed_seed(
    outcome: LegOutcome, request: AnalysisRequest, snapshot: Snapshot, capture: Path
) -> tuple[LegOutcome, SeedAttribution]:
    """Require a complete exact failed playback before attributing its historical seed."""
    run = ROOT / outcome.run_path
    live_path, replay_path = capture / "run-manifest.json", run / "run-manifest.json"
    live = RunManifest.model_validate_json(live_path.read_bytes())
    replay = RunManifest.model_validate_json(replay_path.read_bytes())
    terminal_path = run / "terminal.json"
    terminal = FailureTerminal.model_validate_json(terminal_path.read_bytes())
    original = FailureTerminal.model_validate_json((capture / "terminal.json").read_bytes())
    packets = load_cassettes(capture)
    identity = execution_identity(request, snapshot)
    expected_cassettes = {
        path.stem: sha256_bytes(path.read_bytes()) for path in (capture / "cassettes").glob("*.json")
    }
    if (
        outcome.status != "failed"
        or outcome.error_code not in CONTRACT_FAULTS
        or outcome.effective_seed is not None
        or outcome.requested_seed != request.seed
        or live.mode != "live"
        or replay.mode != "replay"
        or live.identity != identity
        or replay.identity != identity
        or live.boundary_sha256 != semantic_hash(identity)
        or replay.boundary_sha256 != live.boundary_sha256
        or terminal.code != outcome.error_code
        or terminal.stage != outcome.error_stage
        or original.code != terminal.code
        or original.stage != terminal.stage
        or not packets
        or terminal.model_decisions != len(packets)
        or original.model_decisions != len(packets)
        or terminal.network_attempts
        or original.network_attempts
        or terminal.cassette_hashes
        or original.cassette_hashes != expected_cassettes
    ):
        raise ValueError("Failed replay lacks complete exact captured-seed provenance")
    record_path = run.parent.parent / "record.json"
    if LegOutcome.model_validate_json(record_path.read_bytes()) != outcome:
        raise ValueError("Failed replay attribution does not describe its original leg record")
    return outcome.model_copy(update={"effective_seed": identity.seed}), SeedAttribution(
        schema_version=REVISION,
        interpretation="Historical verified model-profile seed, attributed only after exact complete offline playback; no new sampling or provider seed guarantee",
        captured_seed=identity.seed,
        decisions_replayed=len(packets),
        capture_path=str(capture.relative_to(ROOT)) if capture.is_relative_to(ROOT) else str(capture),
        live_manifest_sha256=sha256_bytes(live_path.read_bytes()),
        replay_manifest_sha256=sha256_bytes(replay_path.read_bytes()),
        replay_terminal_sha256=sha256_bytes(terminal_path.read_bytes()),
        original_leg_record_sha256=sha256_bytes(record_path.read_bytes()),
    )


class ReplayMetadataRunner(CampaignRunner):
    """Keep original execution/comparison semantics; repair only failed-leg seed bookkeeping."""

    def manifest(self) -> dict[str, object]:
        return {
            **super().manifest(),
            "replay_metadata_adapter": {
                "revision": REVISION,
                "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
                "collection_policy": "Collect unreachable objects after each physical playback leg; no live or agent configuration change",
            },
        }

    def prepare(self) -> None:
        if self.mode != "replay":
            raise ValueError("Replay metadata adapter cannot execute live inference")
        super().prepare()

    async def leg(
        self, request: AnalysisRequest, snapshot: Snapshot, location: Path, *, capture: Path | None
    ) -> tuple[LegOutcome, AnalysisOutput | None]:
        if self.mode != "replay":
            raise ValueError("Replay metadata adapter cannot execute live inference")
        try:
            outcome, output = await super().leg(request, snapshot, location, capture=capture)
            if outcome.status == "failed" and outcome.error_code in CONTRACT_FAULTS:
                if capture is None:
                    raise ValueError("Failed playback has no registered capture")
                attributed, provenance = attribute_failed_seed(outcome, request, snapshot, capture)
                with (location / "record.before-seed-attribution.json").open("xb") as stream:
                    stream.write((location / "record.json").read_bytes())
                write_json(location / "seed-attribution.json", provenance)
                write_json(location / "record.json", attributed)
                return attributed, output
            return outcome, output
        finally:
            # The first full900 command retained a 30.9GB unreachable heap until
            # Python module finalization. Collection cannot alter live captures.
            gc.collect()
