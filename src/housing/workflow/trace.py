"""Append-only causal events; timestamps never enter semantic agent prompts."""

from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.common import Mode
from housing.identity import canonical_json, semantic_hash


class Trace:
    def __init__(self, directory: Path, run_id: str, mode: Mode, query_hash: str, view_hash: str):
        self.path = directory / "trace.jsonl"
        self.run_id, self.mode = run_id, mode
        self.query_hash, self.view_hash = query_hash, view_hash
        self.sequence = 0

    def emit(
        self,
        event: str,
        actor: str,
        payload: dict[str, object],
        *,
        iteration: int = 0,
        plan_hash: str | None = None,
        parent: int | None = None,
    ) -> int:
        sequence = self.sequence
        body = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "sequence": sequence,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "mode": self.mode,
            "iteration": iteration,
            "event": event,
            "actor": actor,
            "parent_event_sequence": parent,
            "query_sha256": self.query_hash,
            "dataset_view_sha256": self.view_hash,
            "plan_sha256": plan_hash,
            "payload": payload,
            "payload_sha256": semantic_hash(payload),
            "illustrative_fixture": False,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(body) + "\n")
        self.sequence += 1
        return sequence
