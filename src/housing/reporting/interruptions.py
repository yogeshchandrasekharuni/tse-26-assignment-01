"""Validate explicit postmortem declarations without inventing native terminal events."""

from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime

from housing.contracts.common import FrozenModel, NonnegativeInt, Sha256
from housing.identity import sha256_bytes


class ProcessInterruption(FrozenModel):
    schema_version: Literal["process-interruption-1"]
    status: Literal["interrupted"]
    observed_at_utc: AwareDatetime
    reason: Literal["user_reported_mac_restart", "operator_stopped_after_failed_preflight"]
    run_path: str
    recorded_model_responses: NonnegativeInt
    recorded_model_inputs: NonnegativeInt
    provider_attempts_for_unanswered_input: None
    source_hashes: dict[str, Sha256]


def validated_interruption(run: Path, root: Path) -> tuple[ProcessInterruption, Path] | None:
    run, root = run.resolve(), root.resolve()
    if not run.is_relative_to(root / "artifacts/campaigns"):
        return None
    annotation = run.parents[2] / "interruption.json"
    if not annotation.is_file():
        return None
    note = ProcessInterruption.model_validate_json(annotation.read_bytes())
    if (run / "terminal.json").exists() or note.run_path != str(run.relative_to(root)):
        raise ValueError("Interruption conflicts with its recorded run or terminal event")
    actual = {
        str(path.relative_to(root)): sha256_bytes(path.read_bytes())
        for path in sorted(run.rglob("*"))
        if path.is_file()
    }
    if not actual or note.source_hashes != actual:
        raise ValueError("Interrupted capture inventory or bytes differ from its postmortem declaration")
    if note.recorded_model_inputs != len(
        list((run / "model").glob("*.input.json"))
    ) or note.recorded_model_responses != len(list((run / "model").glob("*.response.json"))):
        raise ValueError("Interrupted model-input/response counts differ")
    return note, annotation
