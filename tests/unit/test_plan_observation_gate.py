"""Synthetic acknowledgements exercise the gate; they establish no real delivery."""

import json
from pathlib import Path

import pytest

from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture
from housing.reporting import plan_observability as gate


@pytest.mark.parametrize(
    "fault", ["complete", "accepted_only", "wrong_ids", "wrong_derivation", "changed_screenshot"]
)
def test_gate_requires_complete_unchanged_observation_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    # Actual capture projection, isolated synthetic delivery/QA records. Never written to the registry.
    projection = project_capture(ROOT / gate.CAPTURE_PATH)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "project_capture", lambda _: projection)
    qa_path = tmp_path / gate.QA_PATH
    qa_path.parent.mkdir(parents=True)
    screenshots = {}
    for name in gate.SCREENSHOTS:
        data = ("synthetic-test-image:" + name).encode()
        (qa_path.parent / name).write_bytes(data)
        screenshots[name] = sha256_bytes(data)
    destination = tmp_path / "artifacts/observability/langfuse" / projection.trace_id
    destination.mkdir(parents=True)
    (destination / "projection.json").write_text(projection.model_dump_json())
    receipt = {
        "status": "accepted" if fault == "accepted_only" else "readback_verified",
        "projection_revision": PROJECTION_REVISION,
        "trace_id": projection.trace_id,
        "run_path": str(gate.CAPTURE_PATH),
        "projection_sha256": semantic_hash(projection),
        "observation_count": len(projection.spans),
        "readback_observation_ids_sha256": semantic_hash(
            [] if fault == "wrong_ids" else sorted(projection.span_id(span.key) for span in projection.spans)
        ),
    }
    raw_receipt = json.dumps(receipt).encode()
    (destination / "receipt.json").write_bytes(raw_receipt)
    qa = {
        "schema_version": "langfuse-plan-qa-1",
        "status": "visually_verified",
        "checked_at_utc": "2000-01-01T00:00:00+00:00",
        "projection_revision": PROJECTION_REVISION,
        "run_path": str(gate.CAPTURE_PATH),
        "trace_id": projection.trace_id,
        "projection_sha256": "0" * 64 if fault == "wrong_derivation" else semantic_hash(projection),
        "receipt_sha256": sha256_bytes(raw_receipt),
        "checks": dict.fromkeys(gate.REQUIRED_CHECKS, True),
        "screenshots": screenshots,
    }
    qa_path.write_text(json.dumps(qa))
    if fault == "changed_screenshot":
        (qa_path.parent / "repair-detail.jpg").write_bytes(b"changed")
    if fault == "complete":
        assert len(gate.verify_plan_observability()) == 5
    else:
        with pytest.raises(ValueError, match="readback|derivation|screenshot"):
            gate.verify_plan_observability()


def test_gate_does_not_treat_missing_dashboard_qa_as_offline_preparation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="actual readback and browser proof"):
        gate.verify_plan_observability()
