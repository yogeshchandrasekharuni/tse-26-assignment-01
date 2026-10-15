"""Verify a separately recorded readback of the research-copy projections."""

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime

from housing.contracts.common import FrozenModel, PositiveInt, Sha256
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import CaptureProjection
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture
from housing.reporting.campaign_observability import CurrentDeliveryReceipt, check_receipt
from housing.reporting.interruptions import validated_interruption
from housing.reporting.plan_observability import CAPTURE_PATH, REQUIRED_CHECKS, PlanObservationQa

PROOF_PATH = Path("artifacts/observability/study-readback-v2/verification.json")
PROOF_DIRECTORY = PROOF_PATH.parent


class StudyReadback(FrozenModel):
    schema_version: Literal["langfuse-study-readback-1"]
    status: Literal["verified_complete_readback"]
    checked_at_utc: AwareDatetime
    campaign_id: Literal["headline-live-v1"]
    campaign_artifact_index_sha256: Sha256
    projection_revision: Literal["housing-langfuse-plan-2"]
    destination_id: Sha256
    dashboard_base_url: Literal["http://localhost:19310"]
    project_id: Literal["housing-trajectories"]
    closed_captures: PositiveInt
    observations: PositiveInt
    receipt_hashes: dict[str, Sha256]
    interruption_hashes: dict[str, Sha256]


def verify_study_readback() -> tuple[int, int]:
    """Recompute each projection and check a genuine isolated-server receipt."""
    proof_path = ROOT / PROOF_PATH
    proof = StudyReadback.model_validate_json(proof_path.read_bytes())
    campaign = ROOT / "artifacts/campaigns" / proof.campaign_id
    if not (campaign / "finished.json").is_file():
        raise ValueError("Readback proof requires a completed campaign")
    runtime = json.loads((campaign / "runtime.json").read_bytes())
    if (
        proof.projection_revision != PROJECTION_REVISION
        or proof.campaign_artifact_index_sha256
        != sha256_bytes((campaign / "artifact_hashes.json").read_bytes())
        or proof.closed_captures != runtime["physical_analysis_attempts"]
        or runtime["logical_comparisons"] != 900
    ):
        raise ValueError("Readback proof does not bind this completed campaign")
    receipt_hashes: dict[str, str] = {}
    interruption_hashes: dict[str, str] = {}
    observations = 0
    for run in sorted(campaign.glob("cases/*/attempt-*/*/runs/*")):
        if not run.is_dir():
            continue
        if not (run / "terminal.json").is_file():
            interrupted = validated_interruption(run, ROOT)
            if interrupted is None:
                raise ValueError("Unfinished capture has no interruption record")
            _, annotation = interrupted
            interruption_hashes[str(annotation.relative_to(ROOT))] = sha256_bytes(annotation.read_bytes())
            continue
        projection = project_capture(run)
        receipt_path = proof_path.parent / "receipts" / f"{projection.trace_id}.json"
        if not receipt_path.is_file():
            raise ValueError(f"Readback receipt missing: {run.relative_to(ROOT)}")
        relative = str(receipt_path.relative_to(ROOT))
        digest = sha256_bytes(receipt_path.read_bytes())
        if proof.receipt_hashes.get(relative) != digest:
            raise ValueError("Readback receipt is unbound or changed")
        receipt = CurrentDeliveryReceipt.model_validate_json(receipt_path.read_bytes())
        check_receipt(
            receipt,
            projection,
            destination_id=proof.destination_id,
            dashboard_base_url=proof.dashboard_base_url,
            project_id=proof.project_id,
        )
        receipt_hashes[relative] = digest
        observations += len(projection.spans)
    if (
        receipt_hashes != proof.receipt_hashes
        or interruption_hashes != proof.interruption_hashes
        or len(receipt_hashes) != proof.closed_captures
        or observations != proof.observations
    ):
        raise ValueError("Readback coverage differs from the campaign inventory")
    return len(receipt_hashes), observations


def verify_study_examples() -> None:
    """Bind each freshly read-back example to its unchanged capture."""
    proof = StudyReadback.model_validate_json((ROOT / PROOF_PATH).read_bytes())
    setup = json.loads((ROOT / "artifacts/observability/setup/verified.json").read_bytes())
    if (
        setup["status"] != "verified"
        or setup["health_http_status"] != 200
        or len(setup["services"]) != 6
        or any(row["state"] != "running" for row in setup["services"])
        or sha256_bytes((ROOT / "observability/langfuse/compose.yaml").read_bytes())
        != setup["compose_sha256"]
    ):
        raise ValueError("Source dashboard setup proof is missing or changed")
    index = json.loads((ROOT / "artifacts/observability/demo-index.json").read_bytes())
    examples = index["examples"]
    labels = {row["label"] for row in examples}
    if (
        index["status"] != "verified"
        or labels
        != {
            "normal",
            "natural_feedback",
            "natural_failure",
            "auxiliary_injected_feedback",
        }
        or len(examples) != 4
    ):
        raise ValueError("Recorded example inventory is incomplete")
    for row in examples:
        example = ROOT / PROOF_DIRECTORY / "examples" / row["label"]
        receipt = CurrentDeliveryReceipt.model_validate_json((example / "receipt.json").read_bytes())
        stored = CaptureProjection.model_validate_json((example / "projection.json").read_bytes())
        current = project_capture(ROOT / row["run_path"])
        if (
            semantic_hash(stored) != semantic_hash(current)
            or receipt.observation_count != row["observations"]
        ):
            raise ValueError(f"Example projection differs from its current capture: {row['label']}")
        check_receipt(
            receipt,
            current,
            destination_id=proof.destination_id,
            dashboard_base_url=proof.dashboard_base_url,
            project_id=proof.project_id,
        )
    # These screenshots document the original source-revision inspection. The
    # new readbacks above are independent proof of the current projections.
    source_qa = json.loads((ROOT / "artifacts/observability/qa/inspection.json").read_bytes())
    if source_qa["status"] != "visually_verified":
        raise ValueError("Source dashboard inspection is missing")
    for name, digest in source_qa["screenshots"].items():
        if sha256_bytes((ROOT / "artifacts/observability/qa" / name).read_bytes()) != digest:
            raise ValueError("Source dashboard screenshot changed")


def verify_study_plan_observability() -> tuple[Path, ...]:
    """Verify current repair readback and separately captured browser evidence."""
    proof = StudyReadback.model_validate_json((ROOT / PROOF_PATH).read_bytes())
    directory = ROOT / PROOF_DIRECTORY / "plan-aware-qa"
    qa_path = directory / "inspection.json"
    if not qa_path.is_file():
        raise ValueError("Current study dashboard screenshot proof is missing")
    qa = PlanObservationQa.model_validate_json(qa_path.read_bytes())
    if (
        qa.projection_revision != PROJECTION_REVISION
        or qa.run_path != str(CAPTURE_PATH)
        or set(qa.checks) != REQUIRED_CHECKS
        or not all(qa.checks.values())
        or set(qa.screenshots) != {"trajectory.png", "repair-detail.png"}
    ):
        raise ValueError("Study dashboard inspection does not cover the required repair")
    current = project_capture(ROOT / CAPTURE_PATH)
    receipt_path, projection_path = directory / "receipt.json", directory / "projection.json"
    receipt = CurrentDeliveryReceipt.model_validate_json(receipt_path.read_bytes())
    stored = CaptureProjection.model_validate_json(projection_path.read_bytes())
    if (
        qa.trace_id != current.trace_id
        or qa.projection_sha256 != semantic_hash(current)
        or qa.receipt_sha256 != sha256_bytes(receipt_path.read_bytes())
        or semantic_hash(stored) != semantic_hash(current)
    ):
        raise ValueError("Study dashboard inspection does not bind the current projection")
    check_receipt(
        receipt,
        current,
        destination_id=proof.destination_id,
        dashboard_base_url=proof.dashboard_base_url,
        project_id=proof.project_id,
    )
    paths = [qa_path, receipt_path, projection_path]
    for name, digest in qa.screenshots.items():
        screenshot = directory / name
        if not screenshot.is_file() or sha256_bytes(screenshot.read_bytes()) != digest:
            raise ValueError("Current study dashboard screenshot is missing or changed")
        paths.append(screenshot)
    return tuple(paths)
