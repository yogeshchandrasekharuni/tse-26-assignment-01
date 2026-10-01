"""One production service for API, CLI and evaluation, including strict offline playback."""

import asyncio
import json
import traceback
import uuid
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from housing.agents.fast_agent import FastAgentOrchestrator, prompt_bundle
from housing.contracts.errors import HousingError
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.store import Snapshot
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.replay.network import deny_network
from housing.workflow.boundary import RunManifest, execution_identity, verify_live_model
from housing.workflow.controller import Controller


async def run_analysis(
    request: AnalysisRequest,
    snapshot: Snapshot,
    *,
    artifact_root: Path | None = None,
    mode: Literal["live", "replay"] = "live",
    capture: Path | None = None,
    campaign_id: str | None = None,
) -> AnalysisOutput:
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]
    directory = (artifact_root or ROOT / "artifacts/traces") / run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "request.json", request)
    try:
        identity = execution_identity(request, snapshot)
        boundary_hash = semantic_hash(identity)
        if mode == "replay":
            if capture is None:
                raise HousingError("REPLAY_MISS", "Replay requires a genuine live capture", "capture_load")
            reference = RunManifest.model_validate_json((capture / "run-manifest.json").read_bytes())
            if (
                reference.mode != "live"
                or reference.identity != identity
                or reference.boundary_sha256 != boundary_hash
            ):
                raise ValueError("Live capture execution identity differs")
            terminal = json.loads((capture / "terminal.json").read_bytes())
            if set(terminal["cassette_hashes"]) != {p.stem for p in (capture / "cassettes").glob("*.json")}:
                raise ValueError("Cassette inventory differs from the terminal manifest")
            for name, expected in terminal["cassette_hashes"].items():
                if (
                    not name.isdigit()
                    or sha256_bytes((capture / "cassettes" / f"{name}.json").read_bytes()) != expected
                ):
                    raise ValueError("Captured cassette bytes differ from the terminal manifest")
        elif capture is not None:
            raise HousingError("AGENT_POLICY_ERROR", "A live run cannot consume replay responses", "startup")
    except Exception as error:
        typed = (
            error
            if isinstance(error, HousingError)
            else HousingError("REPLAY_MISS" if mode == "replay" else "TOOL_ERROR", str(error), "capture_load")
        )
        write_json(
            directory / "failure.json",
            {
                "code": typed.code,
                "message": typed.message,
                "stage": typed.stage,
                "traceback": traceback.format_exc(),
            },
        )
        write_json(
            directory / "terminal.json",
            {
                "status": "failed",
                "code": typed.code,
                "stage": typed.stage,
                "model_decisions": 0,
                "network_attempts": [],
                "cassette_hashes": {},
            },
        )
        raise typed from error
    manifest = RunManifest(
        schema_version="production-run-3",
        mode=mode,
        identity=identity,
        boundary_sha256=boundary_hash,
        source_capture=str(capture.relative_to(ROOT))
        if capture and capture.is_relative_to(ROOT)
        else str(capture)
        if capture
        else None,
    )
    write_json(directory / "run-manifest.json", manifest)
    controller = Controller(request, snapshot, directory, run_id, mode, semantic_hash(prompt_bundle()))
    gateway: FastAgentOrchestrator | None = None
    outcome: dict[str, object] = {"status": "failed"}
    network_attempts: list[str] = []
    try:
        with deny_network() if mode == "replay" else nullcontext(network_attempts) as network_attempts:
            if mode == "live":
                await verify_live_model(identity)
            gateway = FastAgentOrchestrator(controller, boundary_hash, capture)
            await gateway.run()
            if network_attempts:
                raise HousingError("REPLAY_MISS", "Network access attempted during playback", "offline_guard")
        if controller.output is None:
            raise HousingError("AGENT_OUTPUT_INVALID", "No finalized output returned", "parent_return")
        output = controller.output
        if campaign_id is not None:
            output = output.model_copy(
                update={"metadata": output.metadata.model_copy(update={"live_campaign_id": campaign_id})}
            )
        write_json(directory / "output.json", output)
        controller.trace.emit(
            "RUN_COMPLETED",
            "orchestrator",
            {
                "output_sha256": semantic_hash(output),
                "output_path": "output.json",
                "quality": output.quality,
                "composition_path": "composition.json",
                "source_capture": manifest.source_capture,
            },
            iteration=controller.plan.version if controller.plan else 0,
            plan_hash=controller.plan.semantic_sha256 if controller.plan else None,
        )
        outcome = {"status": "completed", "canonical_sha256": semantic_hash(output.canonical)}
        return output
    except Exception as error:
        typed = controller.fatal or (
            error
            if isinstance(error, HousingError)
            else HousingError(
                "MODEL_UNAVAILABLE",
                "Inference workflow exceeded its declared time budget",
                "workflow_timeout",
            )
            if isinstance(error, asyncio.TimeoutError)
            else HousingError("TOOL_ERROR", str(error), "workflow")
        )
        failure: dict[str, object] = {
            "code": typed.code,
            "message": typed.message,
            "stage": typed.stage,
            "traceback": traceback.format_exc(),
        }
        write_json(directory / "failure.json", failure)
        controller.trace.emit(
            "RUN_FAILED", "controller", failure, iteration=controller.plan.version if controller.plan else 0
        )
        outcome = {"status": "failed", "code": typed.code, "stage": typed.stage}
        raise typed from error
    finally:
        write_json(
            directory / "terminal.json",
            {
                **outcome,
                "model_decisions": gateway.sequence if gateway else 0,
                "network_attempts": network_attempts,
                "cassette_hashes": {
                    p.stem: sha256_bytes(p.read_bytes())
                    for p in sorted((directory / "cassettes").glob("*.json"))
                },
            },
        )
