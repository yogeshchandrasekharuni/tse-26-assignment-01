"""Require complete current campaign delivery receipts without credentials or network."""

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from housing.contracts.common import FrozenModel, PositiveInt, Sha256
from housing.evaluation.models import HeadlineRow
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import CaptureProjection
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture
from housing.reporting.interruptions import validated_interruption

QA_PATH = Path("artifacts/observability/headline-delivery-v1/verification.json")
type TraceId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class CurrentDeliveryReceipt(FrozenModel):
    schema_version: Literal["housing-langfuse-1"]
    projection_revision: Literal["housing-langfuse-plan-2"]
    status: Literal["readback_verified"]
    run_path: str
    trace_id: TraceId
    projection_sha256: Sha256
    destination_id: Sha256
    observation_count: PositiveInt
    readback_observation_ids_sha256: Sha256
    exported_at_utc: AwareDatetime
    dashboard_url: str
    interpretation: str


class CampaignDeliveryQa(FrozenModel):
    schema_version: Literal["langfuse-campaign-delivery-1"]
    status: Literal["verified_complete_readback"]
    checked_at_utc: AwareDatetime
    campaign_id: Literal["headline-live-v1"]
    campaign_artifact_index_sha256: Sha256
    projection_revision: Literal["housing-langfuse-plan-2"]
    destination_id: Sha256
    dashboard_base_url: Literal["http://localhost:19300"]
    project_id: Literal["housing-trajectories"]
    closed_captures: PositiveInt
    observations: PositiveInt
    receipt_hashes: dict[str, Sha256]
    interruption_hashes: dict[str, Sha256]


def check_receipt(
    receipt: CurrentDeliveryReceipt,
    projection: CaptureProjection,
    *,
    destination_id: str,
    dashboard_base_url: str,
    project_id: str,
) -> None:
    """An accepted payload or a different set of observed spans cannot pass."""
    expected_ids = sorted(projection.span_id(span.key) for span in projection.spans)
    if (
        receipt.projection_revision != PROJECTION_REVISION
        or receipt.trace_id != projection.trace_id
        or receipt.run_path != projection.run_path
        or receipt.projection_sha256 != semantic_hash(projection)
        or receipt.observation_count != len(projection.spans)
        or receipt.readback_observation_ids_sha256 != semantic_hash(expected_ids)
    ):
        raise ValueError("Receipt lacks exact current complete-projection readback")
    expected_url = f"{dashboard_base_url}/project/{project_id}/traces/{projection.trace_id}"
    if receipt.destination_id != destination_id or receipt.dashboard_url != expected_url:
        raise ValueError("Receipt belongs to a different dashboard destination")


def verify_campaign_observability() -> tuple[Path, ...]:
    """Recompute all projections and verify preserved readback; never send or create proof."""
    qa_path = ROOT / QA_PATH
    if not qa_path.is_file():
        raise ValueError("Complete live campaign Langfuse delivery and exact readback proof are required")
    qa = CampaignDeliveryQa.model_validate_json(qa_path.read_bytes())
    campaign = ROOT / "artifacts/campaigns" / qa.campaign_id
    if not (campaign / "finished.json").is_file():
        raise ValueError("Dashboard proof cannot stand in for a closed live campaign")
    rows = [HeadlineRow.model_validate(row) for row in json.loads((campaign / "headline.json").read_bytes())]
    runtime = json.loads((campaign / "runtime.json").read_bytes())
    if (
        len(rows) != 10
        or not all(row.complete and row.completed_bases >= 30 for row in rows)
        or runtime["logical_comparisons"] != 900
        or qa.closed_captures != runtime["physical_analysis_attempts"]
        or qa.campaign_artifact_index_sha256 != sha256_bytes((campaign / "artifact_hashes.json").read_bytes())
    ):
        raise ValueError("Dashboard proof does not bind this complete campaign")
    receipt_hashes: dict[str, str] = {}
    interruption_hashes: dict[str, str] = {}
    observations = 0
    inputs = [qa_path]
    for run in sorted(campaign.glob("cases/*/attempt-*/*/runs/*")):
        if not run.is_dir():
            continue
        if not (run / "terminal.json").is_file():
            interrupted = validated_interruption(run, ROOT)
            if interrupted is None:
                raise ValueError("Dashboard corpus contains an undeclared unfinished capture")
            _, annotation = interrupted
            interruption_hashes[str(annotation.relative_to(ROOT))] = sha256_bytes(annotation.read_bytes())
            inputs.append(annotation)
            continue
        current = project_capture(run)
        receipt_path = qa_path.parent / "receipts" / f"{current.trace_id}.json"
        if not receipt_path.is_file():
            raise ValueError(f"Current campaign dashboard receipt missing: {run.relative_to(ROOT)}")
        digest = sha256_bytes(receipt_path.read_bytes())
        relative = str(receipt_path.relative_to(ROOT))
        if qa.receipt_hashes.get(relative) != digest:
            raise ValueError("A campaign readback acknowledgement is unbound or changed")
        receipt = CurrentDeliveryReceipt.model_validate_json(receipt_path.read_bytes())
        check_receipt(
            receipt,
            current,
            destination_id=qa.destination_id,
            dashboard_base_url=qa.dashboard_base_url,
            project_id=qa.project_id,
        )
        receipt_hashes[relative] = digest
        observations += len(current.spans)
        inputs.append(receipt_path)
    if (
        receipt_hashes != qa.receipt_hashes
        or interruption_hashes != qa.interruption_hashes
        or qa.closed_captures != len(receipt_hashes)
        or qa.observations != observations
    ):
        raise ValueError("Dashboard coverage differs from the full physical capture inventory")
    return tuple(inputs)
