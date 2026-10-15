"""Actual captured delegation/feedback/failure mapped without new inference or network."""

import json
import runpy
import shutil
import sys
from pathlib import Path

import httpx
import pytest

from housing.identity import ROOT, semantic_hash, write_json
from housing.observability import langfuse
from housing.observability.langfuse import LocalLangfuse, project_capture, send_projection, unix_ns

FEEDBACK = ROOT / "artifacts/traces/20261001T144318Z-82736e984f"
FAILED = ROOT / (
    "artifacts/campaigns/headline-live-v1/cases/MR01-b003-s155921/"
    "attempt-001/followup/runs/20261002T033100Z-17d9d8cdf3"
)


def test_real_feedback_capture_preserves_children_receipts_and_causal_loop() -> None:
    projection = project_capture(FEEDBACK)
    assert projection.evidence_scope == "auxiliary_index_omission"
    assert [span.name for span in projection.spans if span.parent_key is None] == ["Orchestrator"]
    generations = [span for span in projection.spans if span.kind == "generation"]
    assert len(generations) == 16
    assert generations[0].end_ns == 1790865864445970000
    assert generations[0].start_ns == 1790865807547946723
    agents = {span.key: span for span in projection.spans if span.kind == "agent"}
    assert [span.name for span in agents.values()] == [
        "Orchestrator",
        "Price · pass 1",
        "Supply · pass 1",
        "Reviewer · pass 1",
        "Price · pass 2",
        "Supply · pass 2",
        "Region · pass 2",
        "Reviewer · pass 2",
        "Composer · pass 2",
    ]
    assert (
        agents["agent-002"].attributes["langfuse.observation.metadata.native_tool_call_id"] == "call_64jdm5td"
    )
    assert (
        agents["agent-003"].attributes["langfuse.observation.metadata.native_tool_call_id"] == "call_nwvgs5ca"
    )
    events = {span.key: span for span in projection.spans if span.key.startswith("event-")}
    assert len(events) == 28
    assert events["event-005"].parent_key == "agent-002"  # Price receipt, first scan.
    assert events["event-016"].parent_key == "agent-008"  # Price receipt after feedback.
    assert events["event-014"].link_keys == ("event-010",)  # Refinement caused by first review.
    assert all(span.start_ns == span.end_ns for span in events.values())
    assert all(span.parent_key == "orchestrator" for key, span in agents.items() if key != "orchestrator")
    payload = projection.otlp()["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len({row["spanId"] for row in payload}) == 53
    assert payload[0].get("parentSpanId") is None
    assert unix_ns("1970-01-01T00:00:00.000001+00:00") == 1000


def test_natural_failure_retains_error_and_never_adds_a_composer() -> None:
    projection = project_capture(FAILED)
    assert projection.evidence_scope == "headline"
    assert projection.spans[0].error
    assert len([span for span in projection.spans if span.kind == "generation"]) == 4
    assert any(span.name == "Price · pass 1" and span.error for span in projection.spans)
    assert next(span for span in projection.spans if span.key == "generation-002").error
    assert any("RUN_FAILED" in span.name and span.error for span in projection.spans)
    assert not any("Composer" in span.name for span in projection.spans)


def test_changed_raw_response_is_not_exported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "artifacts/traces/test-copy"
    shutil.copytree(FEEDBACK, directory)
    monkeypatch.setattr(langfuse, "ROOT", tmp_path)
    path = directory / "model/002.response.json"
    response = json.loads(path.read_bytes())
    response["content"][0]["text"] = "A changed model decision"
    path.write_text(json.dumps(response))
    with pytest.raises(ValueError, match="Model response differs"):
        project_capture(directory)
    manifest_path = directory / "run-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["mode"] = "replay"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Export live captures only"):
        project_capture(directory)


def test_local_transport_refuses_redirects_and_partial_ingestion(tmp_path: Path) -> None:
    projection = project_capture(FAILED)
    env = tmp_path / ".env"
    env.write_text(
        "LANGFUSE_BASE_URL=http://localhost:19300\nLANGFUSE_PUBLIC_KEY=test-public\n"
        "LANGFUSE_SECRET_KEY=test-secret\nLANGFUSE_PROJECT_ID=test\n"
    )
    settings = LocalLangfuse.from_file(env)
    requests: list[str] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(307, headers={"location": "https://example.invalid/collect"})

    with settings.client(httpx.MockTransport(redirect)) as client, pytest.raises(ValueError, match="HTTP307"):
        send_projection(projection, client)
    assert requests == ["http://localhost:19300/api/public/otel/v1/traces"]
    with (
        settings.client(
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200, json={"partialSuccess": {"rejectedSpans": "1", "errorMessage": "rejected"}}
                )
            )
        ) as client,
        pytest.raises(ValueError, match="partial ingestion"),
    ):
        send_projection(projection, client)
    env.write_text(env.read_text().replace("localhost:19300", "example.invalid:19300"))
    with pytest.raises(ValueError, match="authorized only for local"):
        LocalLangfuse.from_file(env)


def test_offline_cli_keeps_a_previously_verified_delivery_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "artifacts/traces/test-copy"
    shutil.copytree(FEEDBACK, directory)
    monkeypatch.setattr(langfuse, "ROOT", tmp_path)
    projection = project_capture(directory)
    destination = tmp_path / "artifacts/observability/langfuse" / projection.trace_id
    receipt_path = destination / "receipt.json"
    # Auxiliary test acknowledgement; no server delivery or empirical result is claimed.
    write_json(receipt_path, {"projection_sha256": semantic_hash(projection), "status": "readback_verified"})
    before = receipt_path.read_bytes()
    namespace = runpy.run_path(str(ROOT / "scripts/export_langfuse.py"), run_name="offline_cli_test")
    monkeypatch.setitem(namespace["main"].__globals__, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["export_langfuse.py", "--run", "artifacts/traces/test-copy", "--dry-run", "--projection", "legacy"],
    )
    namespace["main"]()
    assert receipt_path.read_bytes() == before
    assert json.loads((destination / "preparation.json").read_bytes())["status"] == "prepared_offline"
    assert not (tmp_path / "observability/langfuse/.env").exists()


def test_watcher_resumes_after_a_dashboard_outage_without_new_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "artifacts/runtime/web/test-job/runs/test-copy"
    shutil.copytree(FEEDBACK, directory)
    monkeypatch.setattr(langfuse, "ROOT", tmp_path)
    projection = project_capture(directory)
    env = tmp_path / "observability/langfuse/.env"
    env.parent.mkdir(parents=True)
    env.write_text(
        "LANGFUSE_BASE_URL=http://localhost:19300\nLANGFUSE_PUBLIC_KEY=test-public\n"
        "LANGFUSE_SECRET_KEY=test-secret\nLANGFUSE_PROJECT_ID=test\n"
    )
    posts = 0

    def server(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        if request.method == "POST":
            posts += 1
            if posts == 1:
                raise httpx.ConnectError("Auxiliary test outage", request=request)
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": projection.span_id(span.key), "traceId": projection.trace_id}
                    for span in projection.spans
                ],
                "meta": {},
            },
        )

    original_client = LocalLangfuse.client
    monkeypatch.setattr(
        LocalLangfuse, "client", lambda self: original_client(self, httpx.MockTransport(server))
    )
    namespace = runpy.run_path(str(ROOT / "scripts/export_langfuse.py"), run_name="watch_cli_test")
    monkeypatch.setitem(namespace["main"].__globals__, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["export_langfuse.py", "--web", "--watch", "--verify", "--projection", "legacy"]
    )
    polls = 0

    class EndTest(RuntimeError):
        pass

    def poll(seconds: int) -> None:
        nonlocal polls
        assert seconds == 15
        polls += 1
        if polls == 2:
            raise EndTest

    monkeypatch.setattr(namespace["time"], "sleep", poll)
    with pytest.raises(EndTest):
        namespace["main"]()
    destination = tmp_path / "artifacts/observability/langfuse" / projection.trace_id
    attempts = [json.loads(path.read_bytes()) for path in sorted((destination / "deliveries").glob("*.json"))]
    assert [row["status"] for row in attempts] == ["delivery_failed", "readback_verified"]
    assert attempts[0]["error_type"] == "ConnectError"
    assert posts == 2
    assert json.loads((destination / "receipt.json").read_bytes())["status"] == "readback_verified"
