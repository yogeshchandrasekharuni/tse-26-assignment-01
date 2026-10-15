"""Constructed receipt guards are auxiliary tests, never evidence of dashboard delivery."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from housing.identity import ROOT, semantic_hash
from housing.observability.langfuse import CaptureProjection
from housing.observability.langfuse_plan import project_capture
from housing.reporting import campaign_observability as audit


@pytest.fixture(scope="module")
def projection() -> CaptureProjection:
    return project_capture(ROOT / "artifacts/traces/20261001T150456Z-6c0cbee2b9")


def constructed_receipt(projection: CaptureProjection) -> audit.CurrentDeliveryReceipt:
    return audit.CurrentDeliveryReceipt.model_validate_json(
        json.dumps(
            {
                "schema_version": "housing-langfuse-1",
                "projection_revision": "housing-langfuse-plan-2",
                "status": "readback_verified",
                "run_path": projection.run_path,
                "trace_id": projection.trace_id,
                "projection_sha256": semantic_hash(projection),
                "destination_id": "f" * 64,
                "observation_count": len(projection.spans),
                "readback_observation_ids_sha256": semantic_hash(
                    sorted(projection.span_id(span.key) for span in projection.spans)
                ),
                "exported_at_utc": "2026-10-06T01:23:11+00:00",
                "dashboard_url": f"http://localhost:19300/project/housing-trajectories/traces/{projection.trace_id}",
                "interpretation": "Constructed guard fixture; no real delivery is claimed",
            }
        )
    )


def check(receipt: audit.CurrentDeliveryReceipt, projection: CaptureProjection) -> None:
    audit.check_receipt(
        receipt,
        projection,
        destination_id="f" * 64,
        dashboard_base_url="http://localhost:19300",
        project_id="housing-trajectories",
    )


def test_exact_projection_receipt_shape_is_accepted(projection: CaptureProjection) -> None:
    check(constructed_receipt(projection), projection)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trace_id", "0" * 32),
        ("projection_sha256", "0" * 64),
        ("readback_observation_ids_sha256", "0" * 64),
        ("observation_count", 1),
        ("destination_id", "0" * 64),
    ],
)
def test_receipt_cannot_attest_a_different_trace_span_set_or_destination(
    projection: CaptureProjection, field: str, value: str | int
) -> None:
    raw = constructed_receipt(projection).model_dump(mode="json")
    raw[field] = value
    receipt = audit.CurrentDeliveryReceipt.model_validate_json(json.dumps(raw))
    with pytest.raises(ValueError):
        check(receipt, projection)


def test_http_acceptance_cannot_be_parsed_as_verified_readback(projection: CaptureProjection) -> None:
    raw = constructed_receipt(projection).model_dump(mode="json")
    raw["status"] = "accepted"
    with pytest.raises(ValidationError):
        audit.CurrentDeliveryReceipt.model_validate_json(json.dumps(raw))


def test_missing_whole_campaign_proof_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Complete live campaign Langfuse delivery"):
        audit.verify_campaign_observability()
