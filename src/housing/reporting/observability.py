"""Check preserved local observability proof without requiring Docker or credentials."""

import json

from housing.identity import ROOT, semantic_hash, sha256_bytes
from housing.observability.langfuse import CaptureProjection


def verify_observability() -> None:
    setup = json.loads((ROOT / "artifacts/observability/setup/verified.json").read_bytes())
    if setup["status"] != "verified" or setup["health_http_status"] != 200:
        raise ValueError("Local Langfuse setup has no verified health evidence")
    if sha256_bytes((ROOT / "observability/langfuse/compose.yaml").read_bytes()) != setup["compose_sha256"]:
        raise ValueError("Langfuse configuration differs from exercised Docker setup")
    if len(setup["services"]) != 6 or any(row["state"] != "running" for row in setup["services"]):
        raise ValueError("The isolated six-service Langfuse setup was not running")
    index = json.loads((ROOT / "artifacts/observability/demo-index.json").read_bytes())
    if index["status"] != "verified" or {row["label"] for row in index["examples"]} != {
        "normal",
        "natural_feedback",
        "natural_failure",
        "auxiliary_injected_feedback",
    }:
        raise ValueError("Required observed trajectories are missing")
    for row in index["examples"]:
        receipt_path = (ROOT / row["receipt_path"]).resolve()
        if not receipt_path.is_relative_to(ROOT / "artifacts/observability/demo-receipts"):
            raise ValueError("Demo receipt escapes its evidence registry")
        raw = receipt_path.read_bytes()
        if sha256_bytes(raw) != row["receipt_sha256"]:
            raise ValueError("Preserved Langfuse acknowledgement changed")
        receipt = json.loads(raw)
        projection_path = ROOT / "artifacts/observability/langfuse" / row["trace_id"] / "projection.json"
        projection = CaptureProjection.model_validate_json(projection_path.read_bytes())
        if (
            receipt["status"] != "readback_verified"
            or receipt["trace_id"] != projection.trace_id
            or receipt["projection_sha256"] != semantic_hash(projection)
            or receipt["observation_count"] != len(projection.spans)
            or row["observations"] != len(projection.spans)
            or receipt.get("readback_observation_ids_sha256")
            != semantic_hash(sorted(projection.span_id(span.key) for span in projection.spans))
        ):
            raise ValueError("Langfuse readback does not match its capture projection")
        for name, digest in projection.artifact_hashes.items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or sha256_bytes(path.read_bytes()) != digest:
                raise ValueError("An observed capture changed after export")
    qa = json.loads((ROOT / "artifacts/observability/qa/inspection.json").read_bytes())
    if qa["status"] != "visually_verified":
        raise ValueError("Langfuse browser inspection is missing")
    for name, digest in qa["screenshots"].items():
        if sha256_bytes((ROOT / "artifacts/observability/qa" / name).read_bytes()) != digest:
            raise ValueError("Langfuse proof screenshot changed")
