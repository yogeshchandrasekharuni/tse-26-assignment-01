"""A versioned projection corrects a real repair label without moving legacy observations."""

import json
import runpy
import shutil
import sys
from pathlib import Path

import pytest

from housing.identity import ROOT, semantic_hash
from housing.observability import langfuse, langfuse_plan
from housing.observability.langfuse import CaptureProjection

CAPTURE = ROOT / (
    "artifacts/campaigns/headline-live-v1/cases/MR05-b010-s104729/attempt-001/"
    "followup/runs/20261006T173448Z-9bb7b33a7f"
)


def test_real_refined_repair_has_a_new_identity_correct_parent_and_preserved_raw_tag() -> None:
    legacy = langfuse.project_capture(CAPTURE)
    original = semantic_hash(legacy)
    corrected = langfuse_plan.project_capture(CAPTURE)
    assert corrected.trace_id != legacy.trace_id
    assert semantic_hash(legacy) == original
    assert {legacy.span_id(span.key) for span in legacy.spans}.isdisjoint(
        corrected.span_id(span.key) for span in corrected.spans
    )
    old_repair = next(span for span in legacy.spans if span.key == "event-016")
    repair = next(span for span in corrected.spans if span.key.endswith("/event-016"))
    invalid = next(span for span in corrected.spans if span.key.endswith("/event-015"))
    assert old_repair.parent_key == "agent-002"
    assert repair.parent_key == invalid.parent_key
    assert repair.parent_key is not None and repair.parent_key.endswith("/agent-008")
    assert repair.attributes["langfuse.observation.metadata.recorded_iteration"] == 0
    assert repair.attributes["langfuse.observation.metadata.iteration"] == 1
    assert repair.attributes["langfuse.observation.metadata.iteration_label_basis"] == (
        "plan_and_invalid_decision"
    )
    raw_input = repair.attributes["langfuse.observation.input"]
    assert isinstance(raw_input, str) and json.loads(raw_input)["iteration"] == 0
    old_initial = next(span for span in legacy.spans if span.key == "agent-002")
    initial = next(span for span in corrected.spans if span.key.endswith("/agent-002"))
    refined = next(span for span in corrected.spans if span.key.endswith("/agent-008"))
    assert initial.end_ns < old_initial.end_ns
    assert refined.end_ns >= repair.end_ns
    assert invalid.key in repair.link_keys
    assert all(
        span.attributes["langfuse.observation.metadata.export_version"] == langfuse_plan.PROJECTION_REVISION
        for span in corrected.spans
    )


def test_default_offline_cli_prepares_plan_aware_evidence_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = CAPTURE.relative_to(ROOT)
    directory = tmp_path / relative
    shutil.copytree(CAPTURE, directory)
    for name in langfuse_plan.IMPLEMENTATION_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    monkeypatch.setattr(langfuse, "ROOT", tmp_path)
    monkeypatch.setattr(langfuse_plan, "ROOT", tmp_path)
    expected = langfuse_plan.project_capture(directory)
    namespace = runpy.run_path(str(ROOT / "scripts/export_langfuse.py"), run_name="plan_cli_test")
    monkeypatch.setitem(namespace["main"].__globals__, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["export_langfuse.py", "--run", str(relative), "--dry-run"])
    namespace["main"]()
    destination = tmp_path / "artifacts/observability/langfuse" / expected.trace_id
    projection = CaptureProjection.model_validate_json((destination / "projection.json").read_bytes())
    assert semantic_hash(projection) == semantic_hash(expected)
    preparation = json.loads((destination / "preparation.json").read_bytes())
    assert preparation["status"] == "prepared_offline"
    assert preparation["projection_revision"] == langfuse_plan.PROJECTION_REVISION
    assert not (tmp_path / "observability/langfuse/.env").exists()
