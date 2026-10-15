"""Snapshot actual closed delivery acknowledgements and verify complete physical coverage."""

import json
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture
from housing.reporting.campaign_observability import (
    CampaignDeliveryQa,
    CurrentDeliveryReceipt,
    check_receipt,
    verify_campaign_observability,
)
from housing.reporting.interruptions import validated_interruption

packet = Path(__file__).resolve().parent
operation = json.loads((packet / "operation-result.json").read_bytes())
assert operation["exit_code"] == 0
assert operation["log_sha256"] == sha256_bytes((packet / "export.log").read_bytes())
assert operation["export_script_sha256"] == sha256_bytes((ROOT / "scripts/export_langfuse.py").read_bytes())
campaign = ROOT / "artifacts/campaigns/headline-live-v1"
runtime = json.loads((campaign / "runtime.json").read_bytes())
log = (packet / "export.log").read_text()
receipt_hashes: dict[str, str] = {}
interruption_hashes: dict[str, str] = {}
destination_id: str | None = None
observations = 0
(packet / "receipts").mkdir(exist_ok=False)
for run in sorted(campaign.glob("cases/*/attempt-*/*/runs/*")):
    if not run.is_dir():
        continue
    if not (run / "terminal.json").is_file():
        interruption = validated_interruption(run, ROOT)
        assert interruption is not None
        _, annotation = interruption
        interruption_hashes[str(annotation.relative_to(ROOT))] = sha256_bytes(annotation.read_bytes())
        continue
    projection = project_capture(run)
    original = ROOT / "artifacts/observability/langfuse" / projection.trace_id / "receipt.json"
    payload = original.read_bytes()
    receipt = CurrentDeliveryReceipt.model_validate_json(payload)
    if destination_id is None:
        destination_id = receipt.destination_id
    check_receipt(
        receipt,
        projection,
        destination_id=destination_id,
        dashboard_base_url="http://localhost:19300",
        project_id="housing-trajectories",
    )
    assert f"readback_verified: {projection.run_id} · {len(projection.spans)} observations" in log
    snapshot = packet / "receipts" / f"{projection.trace_id}.json"
    with snapshot.open("xb") as stream:
        stream.write(payload)
    receipt_hashes[str(snapshot.relative_to(ROOT))] = sha256_bytes(payload)
    observations += len(projection.spans)
assert len(receipt_hashes) == runtime["physical_analysis_attempts"] == 1196
assert len(interruption_hashes) == 2 and destination_id is not None
qa = CampaignDeliveryQa(
    schema_version="langfuse-campaign-delivery-1",
    status="verified_complete_readback",
    checked_at_utc=datetime.now(UTC),
    campaign_id="headline-live-v1",
    campaign_artifact_index_sha256=sha256_bytes((campaign / "artifact_hashes.json").read_bytes()),
    projection_revision=PROJECTION_REVISION,
    destination_id=destination_id,
    dashboard_base_url="http://localhost:19300",
    project_id="housing-trajectories",
    closed_captures=len(receipt_hashes),
    observations=observations,
    receipt_hashes=receipt_hashes,
    interruption_hashes=interruption_hashes,
)
write_json(packet / "verification.json", qa)
verified = verify_campaign_observability()
print(
    f"Verified exact actual readback for {len(receipt_hashes):,} terminal captures / {observations:,} observations; "
    f"two interrupted prefixes retained separately; {len(verified):,} offline proof inputs."
)
