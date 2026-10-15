"""Require actual readback and browser proof of the current derived repair mapping."""

import json
from pathlib import Path
from typing import Literal

from housing.contracts.common import FrozenModel, Sha256
from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import CaptureProjection
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture

CAPTURE_PATH = Path(
    "artifacts/campaigns/headline-live-v1/cases/MR05-b010-s104729/attempt-001/"
    "followup/runs/20261006T173448Z-9bb7b33a7f"
)
QA_PATH = Path("artifacts/observability/plan-aware-qa/inspection.json")
REQUIRED_CHECKS = {
    "repair_under_second_pass_price",
    "raw_iteration_and_derived_pass_visible",
    "real_plan_change_visible",
    "terminal_failure_visible",
    "legacy_evidence_preserved",
}
SCREENSHOTS = {"trajectory.jpg", "repair-detail.jpg"}


class PlanObservationQa(FrozenModel):
    schema_version: Literal["langfuse-plan-qa-1"]
    status: Literal["visually_verified"]
    checked_at_utc: str
    projection_revision: Literal["housing-langfuse-plan-2"]
    run_path: str
    trace_id: str
    projection_sha256: Sha256
    receipt_sha256: Sha256
    checks: dict[str, bool]
    screenshots: dict[str, Sha256]


def verify_plan_observability() -> tuple[Path, ...]:
    """Check preserved evidence offline; never deliver, infer or create a QA claim."""
    qa_path = ROOT / QA_PATH
    if not qa_path.is_file():
        raise ValueError("Current plan-aware Langfuse mapping needs actual readback and browser proof")
    qa = PlanObservationQa.model_validate_json(qa_path.read_bytes())
    if (
        qa.projection_revision != PROJECTION_REVISION
        or qa.run_path != str(CAPTURE_PATH)
        or set(qa.checks) != REQUIRED_CHECKS
        or not all(qa.checks.values())
        or set(qa.screenshots) != SCREENSHOTS
    ):
        raise ValueError("Plan-aware dashboard inspection does not cover the required natural repair")
    current = project_capture(ROOT / CAPTURE_PATH)
    if qa.trace_id != current.trace_id or qa.projection_sha256 != semantic_hash(current):
        raise ValueError("Plan-aware browser proof belongs to a different capture or derivation")
    # Preserve actual acknowledgements beside the inspection, as the legacy demo
    # does. A later idempotent import may refresh the mutable delivery timestamp.
    receipt_path, projection_path = qa_path.parent / "receipt.json", qa_path.parent / "projection.json"
    if not receipt_path.is_file() or not projection_path.is_file():
        raise ValueError("Plan-aware delivery acknowledgement or stored projection is missing")
    receipt = json.loads(receipt_path.read_bytes())
    projection = CaptureProjection.model_validate_json(projection_path.read_bytes())
    expected_ids = sorted(current.span_id(span.key) for span in current.spans)
    if (
        sha256_bytes(receipt_path.read_bytes()) != qa.receipt_sha256
        or semantic_hash(projection) != semantic_hash(current)
        or receipt.get("status") != "readback_verified"
        or receipt.get("projection_revision") != PROJECTION_REVISION
        or receipt.get("trace_id") != current.trace_id
        or receipt.get("run_path") != str(CAPTURE_PATH)
        or receipt.get("projection_sha256") != semantic_hash(current)
        or receipt.get("observation_count") != len(current.spans)
        or receipt.get("readback_observation_ids_sha256") != semantic_hash(expected_ids)
    ):
        raise ValueError("Plan-aware acknowledgement lacks exact current observation readback")
    inputs = [qa_path, receipt_path, projection_path]
    for name, digest in qa.screenshots.items():
        screenshot = qa_path.parent / name
        if not screenshot.is_file() or sha256_bytes(screenshot.read_bytes()) != digest:
            raise ValueError("Plan-aware browser screenshot is missing or changed")
        inputs.append(screenshot)
    return tuple(inputs)
