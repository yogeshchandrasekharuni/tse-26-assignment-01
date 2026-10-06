"""Actual ASGI requests and strict schema validation, including production offline replay."""

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from housing.api.app import create_app
from housing.api.models import ClientContracts
from housing.api.registry import CAPTURES
from housing.identity import ROOT, semantic_hash


def validate(name: str, value: object) -> None:
    schema = ClientContracts.model_json_schema()
    Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/" + name}).validate(value)


def test_public_contracts_exports_units_and_path_guards(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        bootstrap = client.get("/api/bootstrap")
        assert bootstrap.status_code == 200
        validate("Bootstrap", bootstrap.json())
        base = client.get("/api/analyses/capture/normal").json()
        changed = client.get("/api/analyses/capture/normal?money=USD_THOUSANDS&area=SQM").json()
        validate("AnalysisView", base)
        validate("AnalysisView", changed)
        assert base["output"]["canonical"] == changed["output"]["canonical"]
        assert base["request"] == changed["request"]
        assert base["months"][-1]["price"] == "$357,060"  # exact half-even from357060.5
        assert changed["months"][-1]["price"] == "$357.1k"
        assert changed["area_unit"] == "m²"
        workflow = client.get("/api/analyses/capture/feedback/workflow").json()
        validate("WorkflowView", workflow)
        assert workflow["refinements"] == 1 and workflow["query_unchanged"]
        assert workflow["evidence_scope"] == "auxiliary_index_omission"
        empty = client.get("/api/analyses/capture/empty").json()
        validate("AnalysisView", empty)
        assert empty["output"]["canonical"]["summary"]["total_observations"] == 0
        assert empty["price_ticks"] == [] and empty["ppsf_ticks"] == []
        assert len(empty["months"]) == 12
        assert all(month["price_plot"]["y"] is None for month in empty["months"])
        assert all(month["observations"] == "0" for month in empty["months"])
        assert all(month["price_mom"] == "Unavailable" for month in empty["months"])
        csv = client.get("/api/analyses/capture/normal/export.csv?area=SQM")
        assert csv.status_code == 200 and "display_median_price_per_SQM_USD" in csv.text
        assert len(csv.text.splitlines()) == 13
        assert client.get("/api/analyses/capture/not-a-capture").status_code == 404
        assert client.get("/api/jobs/not-an-id").status_code == 404
        assert client.get("/api/analyses/capture/normal?area=anything").status_code == 422
        invalid = {
            "request": CAPTURES["normal"].request().model_dump(mode="json"),
            "mode": "replay",
            "capture_id": "normal",
            "path": "/etc/passwd",
        }
        rejected = client.post("/api/jobs", json=invalid)
        assert rejected.status_code == 422
        validate("ErrorInfo", rejected.json())
        published = client.get("/openapi.json").json()
        error_schema = published["paths"]["/api/jobs"]["post"]["responses"]["422"]["content"][
            "application/json"
        ]["schema"]
        assert error_schema == {"$ref": "#/components/schemas/ErrorInfo"}
        Draft202012Validator(published["components"]["schemas"]["ErrorInfo"]).validate(rejected.json())
        assert client.get("/api/jobs").json() == []


def test_web_job_reenters_the_shared_production_service_and_rejects_changed_replay(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        request = CAPTURES["normal"].request().model_dump(mode="json")
        invalid_request = {**request, "window_end": "2026-08"}
        refused = client.post(
            "/api/jobs", json={"request": invalid_request, "mode": "replay", "capture_id": "normal"}
        )
        assert refused.status_code == 409 and refused.json()["code"] == "REPLAY_MISS"
        response = client.post(
            "/api/jobs", json={"request": request, "mode": "replay", "capture_id": "normal"}
        )
        assert response.status_code == 202
        validate("Job", response.json())
        job_id = response.json()["id"]
        deadline = time.monotonic() + 15
        job = response.json()
        while job["state"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(0.02)
            job = client.get("/api/jobs/" + job_id).json()
        validate("Job", job)
        assert job["state"] == "completed", job
        assert job["output"]["metadata"]["mode"] == "replay"
        displayed = client.get("/api/analyses/job/" + job_id).json()
        validate("AnalysisView", displayed)
        assert semantic_hash(displayed["output"]["canonical"]) == semantic_hash(job["output"]["canonical"])
        workflow = client.get("/api/analyses/job/" + job_id + "/workflow").json()
        assert len([event for event in workflow["events"] if event["event"] == "TOOL_COMPLETED"]) == 2
        assert list(tmp_path.glob(job_id + "/runs/*/terminal.json"))


def test_refined_repair_pass_is_annotated_without_rewriting_the_raw_trace(tmp_path: Path) -> None:
    case = ROOT / "artifacts/campaigns/headline-live-v1/cases/MR05-b010-s104729/result.json"
    record = json.loads(case.read_bytes())
    raw_trace = (ROOT / record["followup"]["run_path"] / "trace.jsonl").read_bytes()
    base = "/api/experiments/headline-live-v1/cases/MR05-b010-s104729/followup"
    with TestClient(create_app(tmp_path)) as client:
        response = client.get(base + "/workflow")
        assert response.status_code == 200
        workflow = response.json()
        validate("WorkflowView", workflow)
        assert workflow["status"] == "failed" and workflow["refinements"] == 1
        repair = next(event for event in workflow["events"] if event["event"] == "AGENT_REPAIR")
        assert repair["iteration"] == 0
        assert repair["display_iteration"] == 1
        assert repair["iteration_label_basis"] == "plan_and_invalid_decision"
        for event in workflow["events"]:
            if event["event"] != "AGENT_REPAIR":
                assert event["display_iteration"] == event["iteration"]
                assert event["iteration_label_basis"] == "recorded"
        exported = client.get(base + "/trace")
        assert exported.status_code == 200 and exported.content == raw_trace
        raw_repair = next(
            json.loads(line)
            for line in exported.content.splitlines()
            if json.loads(line)["event"] == "AGENT_REPAIR"
        )
        assert raw_repair["iteration"] == 0 and "display_iteration" not in raw_repair
