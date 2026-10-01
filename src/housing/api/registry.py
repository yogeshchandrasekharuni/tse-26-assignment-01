"""Trusted IDs map to local evidence; browser input never becomes a filesystem path."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from housing.api.models import CaptureId, CaptureSummary
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.store import Snapshot, load_snapshot
from housing.identity import ROOT


@dataclass(frozen=True)
class CaptureBinding:
    directory: Path
    request_path: Path
    title: str
    description: str
    index_omission: bool = False

    def request(self) -> AnalysisRequest:
        return AnalysisRequest.model_validate_json(self.request_path.read_bytes())

    def snapshot(self) -> Snapshot:
        snapshot = frozen_snapshot()
        if self.index_omission:
            request = self.request()
            snapshot = snapshot.omit_index_partitions(
                frozenset({(request.visible_months[0], request.criteria.zips[0])})
            )
        return snapshot

    def summary(self, capture_id: CaptureId) -> CaptureSummary:
        terminal = json.loads((self.directory / "terminal.json").read_bytes())
        return CaptureSummary(
            id=capture_id,
            title=self.title,
            description=self.description,
            purpose="auxiliary_index_omission" if self.index_omission else "development_smoke",
            request=self.request(),
            model_decisions=terminal["model_decisions"],
        )


CAPTURES: dict[CaptureId, CaptureBinding] = {
    "normal": CaptureBinding(
        ROOT / "artifacts/traces/20261001T150456Z-6c0cbee2b9",
        ROOT / "configs/example-request.json",
        "Full synthetic feed",
        "A genuine live development run over all twelve ZIPs; a complete normal route.",
    ),
    "feedback": CaptureBinding(
        ROOT / "artifacts/traces/20261001T144318Z-82736e984f",
        ROOT / "configs/sparse-request.json",
        "Feedback in action",
        "Auxiliary control: an omitted index partition triggers a full CSV rescan and Region diagnosis; two observations become three.",
        True,
    ),
}


@lru_cache(maxsize=1)
def frozen_snapshot() -> Snapshot:
    return load_snapshot(CSV_PATH, MANIFEST_PATH)


def read_output(directory: Path) -> AnalysisOutput:
    return AnalysisOutput.model_validate_json((directory / "output.json").read_bytes())


def campaign_registry() -> dict[str, Path]:
    return {
        path.parent.name: path.parent
        for path in sorted((ROOT / "artifacts/campaigns").glob("*/manifest.json"))
    }
