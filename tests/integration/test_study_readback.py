"""Regression checks for the separately verified dashboard projection."""

import pytest

from housing.identity import ROOT
from housing.observability.langfuse_plan import project_capture
from housing.reporting.campaign_observability import CurrentDeliveryReceipt, check_receipt
from housing.reporting.plan_observability import CAPTURE_PATH
from housing.reporting.study_readback import (
    PROOF_DIRECTORY,
    PROOF_PATH,
    StudyReadback,
    verify_study_plan_observability,
)


def test_study_plan_proof_binds_current_capture_and_screenshots() -> None:
    assert len(verify_study_plan_observability()) == 5


def test_study_readback_rejects_changed_observation_ids_and_destination() -> None:
    proof = StudyReadback.model_validate_json((ROOT / PROOF_PATH).read_bytes())
    receipt_path = ROOT / PROOF_DIRECTORY / "plan-aware-qa" / "receipt.json"
    receipt = CurrentDeliveryReceipt.model_validate_json(receipt_path.read_bytes())
    current = project_capture(ROOT / CAPTURE_PATH)
    kwargs = {
        "destination_id": proof.destination_id,
        "dashboard_base_url": proof.dashboard_base_url,
        "project_id": proof.project_id,
    }
    check_receipt(receipt, current, **kwargs)
    with pytest.raises(ValueError, match="complete-projection readback"):
        check_receipt(
            receipt.model_copy(update={"readback_observation_ids_sha256": "0" * 64}), current, **kwargs
        )
    with pytest.raises(ValueError, match="different dashboard destination"):
        check_receipt(receipt, current, **{**kwargs, "destination_id": "0" * 64})
