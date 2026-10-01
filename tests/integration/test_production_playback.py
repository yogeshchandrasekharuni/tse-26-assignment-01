"""The genuine development capture re-enters Fast Agent with sockets denied."""

import json
import shutil
from pathlib import Path

import pytest

from housing.contracts.errors import HousingError
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.store import load_snapshot
from housing.identity import ROOT, semantic_hash
from housing.workflow.controller import Controller
from housing.workflow.service import run_analysis

CAPTURE = ROOT / "artifacts/traces/20261001T150456Z-6c0cbee2b9"
FEEDBACK = ROOT / "artifacts/traces/20261001T144318Z-82736e984f"


@pytest.mark.asyncio
@pytest.mark.parametrize("feedback", [False, True])
async def test_production_playback_executes_tools_offline(tmp_path: Path, feedback: bool) -> None:
    capture = FEEDBACK if feedback else CAPTURE
    # A minimal source contains no saved answer, numeric result, receipt or trace.
    minimal = tmp_path / "source"
    minimal.mkdir()
    for name in ("run-manifest.json", "terminal.json"):
        shutil.copyfile(capture / name, minimal / name)
    shutil.copytree(capture / "cassettes", minimal / "cassettes")
    request = AnalysisRequest.model_validate_json(
        (ROOT / "configs" / ("sparse-request.json" if feedback else "example-request.json")).read_bytes()
    )
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    if feedback:
        snapshot = snapshot.omit_index_partitions(
            frozenset({(request.visible_months[0], request.criteria.zips[0])})
        )
    output = await run_analysis(
        request,
        snapshot,
        mode="replay",
        capture=minimal,
        artifact_root=tmp_path / "runs",
    )
    expected = json.loads((capture / "terminal.json").read_bytes())
    assert semantic_hash(output.canonical) == expected["canonical_sha256"]
    directory = tmp_path / "runs" / output.metadata.run_id
    terminal = json.loads((directory / "terminal.json").read_bytes())
    assert terminal["network_attempts"] == [] and terminal["model_decisions"] == (16 if feedback else 9)
    trace = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    tools = [event for event in trace if event["event"] == "TOOL_COMPLETED"]
    assert len(tools) == (5 if feedback else 2)
    assert {event["actor"] for event in tools} == (
        {"price", "supply", "region"} if feedback else {"price", "supply"}
    )
    assert output.metadata.mode == "replay"
    if feedback:
        reviews = [e["payload"]["decision"]["decision"] for e in trace if e["event"] == "REVIEW_DECIDED"]
        assert reviews == ["REFINE", "ACCEPT_LIMITED"]
        assert output.canonical.summary.total_observations == 3
        assert sum(e["event"] == "REFINEMENT_APPLIED" for e in trace) == 1


@pytest.mark.asyncio
async def test_changed_current_tool_receipt_fails_before_next_playback_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Controller.context

    def changed_context(controller: Controller) -> dict[str, object]:
        context = original(controller)
        if controller.executions:
            context["receipt_hashes"] = {role: "0" * 64 for role in controller.executions}
        return context

    monkeypatch.setattr(Controller, "context", changed_context)
    request = AnalysisRequest.model_validate_json((ROOT / "configs/example-request.json").read_bytes())
    with pytest.raises(HousingError) as failure:
        await run_analysis(
            request,
            load_snapshot(CSV_PATH, MANIFEST_PATH),
            mode="replay",
            capture=CAPTURE,
            artifact_root=tmp_path,
        )
    assert failure.value.code == "REPLAY_MISS"
    run = next(tmp_path.iterdir())
    events = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines()]
    assert any(event["event"] == "TOOL_COMPLETED" for event in events)
    assert len(list((run / "model").glob("*.response.json"))) < 9
