"""Local FastAPI interface with trusted dataset/evidence IDs and persistent background jobs."""

import asyncio
import csv
import io
import json
import platform
from contextlib import asynccontextmanager, suppress
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path
from typing import Literal, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from housing.api.formatting import analysis_view, rounded
from housing.api.jobs import Jobs
from housing.api.models import (
    AnalysisView,
    Bootstrap,
    CampaignOverview,
    CaptureId,
    CaseDetail,
    CaseIndexItem,
    CatalogEntry,
    ClientContracts,
    ErrorInfo,
    ExperimentView,
    HeadlineDisplay,
    Job,
    ModelTurn,
    Submission,
    TraceEvent,
    WorkflowView,
)
from housing.api.registry import CAPTURES, campaign_registry, read_output
from housing.contracts.common import Mode
from housing.contracts.errors import HousingError
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest, Display
from housing.data.generate import MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.evaluation.models import CaseResult, Cohort
from housing.identity import ROOT
from housing.tools.aggregate import present

type Money = Literal["USD", "USD_THOUSANDS"]
type Area = Literal["SQFT", "SQM"]
type Kind = Literal["capture", "job"]
type Resolved = tuple[
    AnalysisOutput,
    AnalysisRequest,
    Path,
    Literal["live_capture", "live", "replay"],
    Literal["analysis", "development_smoke", "auxiliary_index_omission"],
]


def create_app(runtime_root: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        jobs = Jobs(runtime_root)
        application.state.jobs = jobs
        jobs.recover()
        worker = asyncio.create_task(jobs.worker())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    application = FastAPI(title="Housing Evidence", version="1.0.0", lifespan=lifespan)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

    @application.exception_handler(HousingError)
    async def housing_error(_: Request, error: HousingError) -> JSONResponse:
        status = (
            429
            if error.stage == "web_queue"
            else 409
            if error.code == "REPLAY_MISS"
            else 503
            if error.code == "MODEL_UNAVAILABLE"
            else 400
        )
        return JSONResponse(
            ErrorInfo(code=error.code, message=error.message, stage=error.stage).model_dump(),
            status_code=status,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        errors = "; ".join(
            ".".join(str(x) for x in item["loc"]) + ": " + item["msg"] for item in error.errors()
        )
        return JSONResponse(
            ErrorInfo(code="INVALID_REQUEST", message=errors, stage="request_validation").model_dump(),
            status_code=422,
        )

    @application.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            ErrorInfo(
                code="NOT_FOUND" if error.status_code == 404 else "NOT_READY",
                message=str(error.detail),
                stage="web_lookup",
            ).model_dump(),
            status_code=error.status_code,
        )

    def jobs_for(request: Request) -> Jobs:
        return cast(Jobs, request.app.state.jobs)

    def job_for(job_id: str, request: Request) -> Job:
        job = jobs_for(request).store.get(job_id)
        if job is None:
            raise HTTPException(404, "Analysis job not found")
        return job

    def resolve(kind: Kind, reference: str, request: Request) -> Resolved:
        if kind == "capture":
            if reference not in CAPTURES:
                raise HTTPException(404, "Recorded analysis not found")
            binding = CAPTURES[cast(CaptureId, reference)]
            return (
                read_output(binding.directory),
                binding.request(),
                binding.directory,
                "live_capture",
                "auxiliary_index_omission" if binding.index_omission else "development_smoke",
            )
        job = job_for(reference, request)
        if job.output is None:
            raise HTTPException(409, "This analysis has not produced a completed output")
        directory = (jobs_for(request).root / job.id / "runs" / job.output.metadata.run_id).resolve()
        if not directory.is_relative_to(jobs_for(request).root.resolve()):
            raise HTTPException(404, "Analysis evidence is outside the local artifact registry")
        return (
            job.output,
            job.submission.request,
            directory,
            job.submission.mode,
            "auxiliary_index_omission" if job.submission.capture_id == "feedback" else "analysis",
        )

    def workflow_path(directory: Path, run_id: str, mode: Mode, base_url: str) -> WorkflowView:
        text = (directory / "trace.jsonl").read_text() if (directory / "trace.jsonl").exists() else ""
        lines = text.splitlines() if text.endswith("\n") else text.splitlines()[:-1]
        events = tuple(TraceEvent.model_validate_json(line) for line in lines)
        terminal = (
            json.loads((directory / "terminal.json").read_bytes())
            if (directory / "terminal.json").exists()
            else {
                "model_decisions": len(list((directory / "model").glob("*.input.json"))),
                "status": "running",
            }
        )
        failure = (
            json.loads((directory / "failure.json").read_bytes())
            if (directory / "failure.json").exists()
            else None
        )
        return WorkflowView.model_validate(
            {
                "run_id": run_id,
                "mode": mode,
                "events": events,
                "model_decisions": terminal["model_decisions"],
                "refinements": sum(e.event == "REFINEMENT_APPLIED" for e in events),
                "schema_repairs": sum(e.event == "AGENT_REPAIR" for e in events),
                "query_unchanged": len({e.query_sha256 for e in events}) == 1,
                "trace_url": base_url + "/trace",
                "status": terminal["status"],
                "failure": ErrorInfo(code=failure["code"], message=failure["message"], stage=failure["stage"])
                if failure
                else None,
            }
        )

    def workflow(resolved: Resolved, base_url: str) -> WorkflowView:
        output, _, directory, _, _ = resolved
        return workflow_path(directory, output.metadata.run_id, output.metadata.mode, base_url)

    def view(resolved: Resolved, base_url: str, money: Money | None, area: Area | None) -> AnalysisView:
        output, query, _, origin, purpose = resolved
        return analysis_view(
            output, query, reference=base_url, origin=origin, purpose=purpose, money=money, area=area
        )

    def export_csv(resolved: Resolved, money: Money | None, area: Area | None) -> Response:
        output, query, _, _, _ = resolved
        shown = present(
            output.canonical, Display(money=money or query.display.money, area=area or query.display.area)
        )
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "month",
                "observations",
                "median_price_usd",
                "median_individual_ppsf_usd",
                "price_mom_pct",
                "price_yoy_pct",
                f"display_median_price_{shown.money}",
                f"display_median_price_per_{shown.area}_{shown.money}",
                "run_id",
                "synthetic",
            ]
        )
        for row, presentation in zip(output.canonical.monthly, shown.monthly, strict=True):
            writer.writerow(
                [
                    row.month,
                    row.listing_count,
                    row.median_price_usd,
                    row.median_ppsf_usd,
                    row.price_mom_pct,
                    row.price_yoy_pct,
                    presentation.median_price,
                    presentation.median_price_per_area,
                    output.metadata.run_id,
                    "true",
                ]
            )
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="housing-{output.metadata.run_id}.csv"'},
        )

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ready",
            "dataset": "synthetic",
            "live_model": "local Ollama required; no inference performed by this health check",
        }

    # Pydantic 2.14's Annotated response wrapper rebuilds shared alias validators
    # outside the model's python-re config. Models still validate at construction
    # and file ingestion; public JSON schemas below describe those exact models.
    @application.get(
        "/api/bootstrap",
        response_model=None,
        responses={
            200: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Bootstrap"}}}}
        },
    )
    async def bootstrap() -> Bootstrap:
        catalog = json.loads((ROOT / "housing-tse-codex-handoff/templates/mr_definitions.json").read_bytes())
        return Bootstrap(
            default_request=CAPTURES["normal"].request(),
            captures=tuple(binding.summary(key) for key, binding in CAPTURES.items()),
            dataset=DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes()),
            seed_values=(104729, 130363, 155921),
            contract_version="1.0",
            python_version=platform.python_version(),
            fast_agent_version=version("fast-agent-mcp"),
            live_model_profile="Qwen3.5 9B · frozen v4 seed profiles",
            live_model_requirements="Live analysis uses local Ollama at127.0.0.1:11434. Exact replay needs no running model.",
            mr_catalog=tuple(
                CatalogEntry(
                    id=row["id"],
                    title=row["name"],
                    family=row["family"],
                    relation=row["relation"],
                    preconditions=tuple(row["valid_subdomain"]),
                    compared_fields=tuple(row["compared_fields"]),
                    tolerances=row["tolerances"],
                    witness=row["witness"],
                )
                for row in catalog
            ),
        )

    @application.post(
        "/api/jobs",
        response_model=None,
        status_code=202,
        responses={202: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Job"}}}}},
    )
    async def create_job(submission: Submission, request: Request) -> Job:
        return jobs_for(request).create(submission)

    @application.get(
        "/api/jobs",
        response_model=None,
        responses={
            200: {
                "content": {
                    "application/json": {
                        "schema": {"type": "array", "items": {"$ref": "#/components/schemas/Job"}}
                    }
                }
            }
        },
    )
    async def all_jobs(request: Request) -> tuple[Job, ...]:
        return jobs_for(request).store.all()

    @application.get(
        "/api/jobs/{job_id}",
        response_model=None,
        responses={200: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Job"}}}}},
    )
    async def get_job(job_id: str, request: Request) -> Job:
        return job_for(job_id, request)

    @application.get(
        "/api/analyses/{kind}/{reference}",
        response_model=None,
        responses={
            200: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/AnalysisView"}}}}
        },
    )
    async def get_analysis(
        kind: Kind, reference: str, request: Request, money: Money | None = None, area: Area | None = None
    ) -> AnalysisView:
        return view(resolve(kind, reference, request), f"/api/analyses/{kind}/{reference}", money, area)

    @application.get("/api/analyses/{kind}/{reference}/workflow", response_model=WorkflowView)
    async def get_workflow(kind: Kind, reference: str, request: Request) -> WorkflowView:
        if kind == "job":
            job = job_for(reference, request)
            runs = list((jobs_for(request).root / job.id / "runs").glob("*"))
            if len(runs) != 1:
                raise HTTPException(409, "This queued job has not started its evidence trace")
            return workflow_path(
                runs[0], runs[0].name, job.submission.mode, f"/api/analyses/{kind}/{reference}"
            )
        return workflow(resolve(kind, reference, request), f"/api/analyses/{kind}/{reference}")

    @application.get("/api/analyses/{kind}/{reference}/export.json", response_class=Response)
    async def json_export(kind: Kind, reference: str, request: Request) -> Response:
        output = resolve(kind, reference, request)[0]
        return Response(
            output.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="housing-{output.metadata.run_id}.json"'},
        )

    @application.get("/api/analyses/{kind}/{reference}/export.csv", response_class=Response)
    async def csv_export(
        kind: Kind, reference: str, request: Request, money: Money | None = None, area: Area | None = None
    ) -> Response:
        return export_csv(resolve(kind, reference, request), money, area)

    @application.get("/api/analyses/{kind}/{reference}/trace", response_class=Response)
    async def trace_export(kind: Kind, reference: str, request: Request) -> Response:
        if kind == "job":
            job = job_for(reference, request)
            runs = list((jobs_for(request).root / job.id / "runs").glob("*"))
            if len(runs) != 1 or not (runs[0] / "trace.jsonl").exists():
                raise HTTPException(409, "No trace has been emitted for this job yet")
            directory = runs[0]
        else:
            directory = resolve(kind, reference, request)[2]
        return Response(
            (directory / "trace.jsonl").read_bytes(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": 'attachment; filename="trace.jsonl"'},
        )

    def campaign_for(campaign_id: str) -> Path:
        directory = campaign_registry().get(campaign_id)
        if directory is None:
            raise HTTPException(404, "Experiment campaign not found")
        return directory

    def case_for(campaign_id: str, key: str) -> tuple[CaseResult, Path]:
        directory = campaign_for(campaign_id)
        allowed = {p.parent.name: p for p in (directory / "cases").glob("*/result.json")}
        if key not in allowed:
            raise HTTPException(404, "Completed comparison not found")
        return CaseResult.model_validate_json(allowed[key].read_bytes()), directory

    def case_leg(campaign_id: str, key: str, leg: Literal["source", "followup"]) -> Resolved:
        result, _ = case_for(campaign_id, key)
        evidence = result.source if leg == "source" else result.followup
        directory = (ROOT / evidence.run_path).resolve()
        if not directory.is_relative_to(ROOT / "artifacts/campaigns"):
            raise HTTPException(404, "Case evidence is outside the campaign registry")
        if evidence.status != "completed":
            raise HTTPException(409, "This leg failed; inspect the case error and preserved attempt")
        return (
            read_output(directory),
            AnalysisRequest.model_validate_json((directory / "request.json").read_bytes()),
            directory,
            result.mode,
            "analysis",
        )

    @application.get("/api/experiments", response_model=ExperimentView)
    async def experiments() -> ExperimentView:
        campaigns = []
        for campaign_id, directory in campaign_registry().items():
            manifest = json.loads((directory / "manifest.json").read_bytes())
            progress = (
                json.loads((directory / "progress.json").read_bytes())
                if (directory / "progress.json").exists()
                else {}
            )
            headlines = (
                tuple(
                    HeadlineDisplay.model_validate_json(
                        json.dumps(
                            {
                                **row,
                                "base_rate_label": rounded(Fraction(row["base_rate"]) * 100, 2) + "%"
                                if row["base_rate"] is not None
                                else "Undefined",
                                "ci95_label": rounded(Fraction(row["ci95_low"]) * 100, 2)
                                + "% – "
                                + rounded(Fraction(row["ci95_high"]) * 100, 2)
                                + "%"
                                if row["ci95_low"] is not None
                                else "Undefined",
                            }
                        )
                    )
                    for row in json.loads((directory / "headline.json").read_bytes())
                )
                if (directory / "headline.json").exists()
                else ()
            )
            expected = manifest["expected_comparisons"]
            complete = bool(headlines) and all(row.complete for row in headlines)
            campaigns.append(
                CampaignOverview(
                    id=campaign_id,
                    mode=manifest["mode"],
                    scope="pilot" if expected == 9 else "headline" if expected == 900 else "auxiliary",
                    expected_comparisons=expected,
                    completed_comparisons=progress.get("completed_comparisons", 0),
                    state="complete"
                    if complete
                    else "incomplete"
                    if (directory / "finished.json").exists()
                    else "running",
                    headlines=headlines,
                    last_case=progress.get("last_case"),
                    last_status=progress.get("last_status"),
                    seeds=tuple(manifest["seeds"]),
                    cohort_path=manifest["cohort_path"],
                )
            )
        return ExperimentView(campaigns=tuple(campaigns))

    @application.get("/api/experiments/{campaign_id}/cases", response_model=tuple[CaseIndexItem, ...])
    async def case_index(campaign_id: str) -> tuple[CaseIndexItem, ...]:
        directory = campaign_for(campaign_id)
        items = []
        for path in sorted((directory / "cases").glob("*/result.json")):
            result = CaseResult.model_validate_json(path.read_bytes())
            items.append(
                CaseIndexItem(
                    key=path.parent.name,
                    mr_id=result.mr_id,
                    base_id=result.base_id,
                    seed=result.seed,
                    status=result.status,
                    violation_kind=result.violation_kind,
                    source_reused=result.source_reused_from is not None,
                )
            )
        return tuple(items)

    @application.get(
        "/api/experiments/{campaign_id}/cases/{key}",
        response_model=None,
        responses={
            200: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CaseDetail"}}}}
        },
    )
    async def case_detail(campaign_id: str, key: str) -> CaseDetail:
        result, directory = case_for(campaign_id, key)
        manifest = json.loads((directory / "manifest.json").read_bytes())
        cohort = Cohort.model_validate_json((ROOT / manifest["cohort_path"]).read_bytes())
        spec = next(c for c in cohort.cases if c.mr == result.mr_id and c.base_id == result.base_id)
        base = f"/api/experiments/{campaign_id}/cases/{key}"
        source = (
            view(case_leg(campaign_id, key, "source"), base + "/source", None, None)
            if result.source.status == "completed"
            else None
        )
        followup = (
            view(case_leg(campaign_id, key, "followup"), base + "/followup", None, None)
            if result.followup.status == "completed"
            else None
        )
        return CaseDetail(
            result=result,
            source=source,
            followup=followup,
            witness=spec.eligibility.witnesses,
            recipe=spec.recipe.model_dump(mode="json"),
        )

    @application.get("/api/experiments/{campaign_id}/cases/{key}/{leg}/workflow", response_model=WorkflowView)
    async def case_workflow(campaign_id: str, key: str, leg: Literal["source", "followup"]) -> WorkflowView:
        result, _ = case_for(campaign_id, key)
        evidence = result.source if leg == "source" else result.followup
        directory = (ROOT / evidence.run_path).resolve()
        if not directory.is_relative_to(ROOT / "artifacts/campaigns"):
            raise HTTPException(404, "Case evidence is outside the campaign registry")
        return workflow_path(
            directory, evidence.run_id, result.mode, f"/api/experiments/{campaign_id}/cases/{key}/{leg}"
        )

    @application.get("/api/experiments/{campaign_id}/cases/{key}/{leg}/export.json", response_class=Response)
    async def case_json(campaign_id: str, key: str, leg: Literal["source", "followup"]) -> Response:
        return Response(
            case_leg(campaign_id, key, leg)[0].model_dump_json(indent=2), media_type="application/json"
        )

    @application.get("/api/experiments/{campaign_id}/cases/{key}/{leg}/export.csv", response_class=Response)
    async def case_csv(campaign_id: str, key: str, leg: Literal["source", "followup"]) -> Response:
        return export_csv(case_leg(campaign_id, key, leg), None, None)

    @application.get("/api/experiments/{campaign_id}/cases/{key}/{leg}/trace", response_class=Response)
    async def case_trace(campaign_id: str, key: str, leg: Literal["source", "followup"]) -> Response:
        result, _ = case_for(campaign_id, key)
        evidence = result.source if leg == "source" else result.followup
        directory = (ROOT / evidence.run_path).resolve()
        if (
            not directory.is_relative_to(ROOT / "artifacts/campaigns")
            or not (directory / "trace.jsonl").exists()
        ):
            raise HTTPException(404, "No emitted case trace is available")
        return Response(
            (directory / "trace.jsonl").read_bytes(),
            media_type="application/x-ndjson",
        )

    def model_turn(directory: Path, sequence: int) -> ModelTurn:
        path = directory / "model" / f"{sequence:03d}.input.json"
        if not path.is_file():
            raise HTTPException(404, "Model decision evidence not found")

        def read(suffix: str):
            candidate = path.with_name(f"{sequence:03d}.{suffix}.json")
            return json.loads(candidate.read_bytes()) if candidate.is_file() else None

        return ModelTurn(
            sequence=sequence,
            input=read("input"),
            response=read("response"),
            dispatched=read("dispatched"),
            budget=read("budget") or {},
        )

    @application.get("/api/analyses/{kind}/{reference}/model/{sequence}", response_model=ModelTurn)
    async def get_model_turn(
        kind: Kind, reference: str, request: Request, sequence: int = PathParam(ge=0, le=70)
    ) -> ModelTurn:
        if kind == "job":
            job = job_for(reference, request)
            runs = list((jobs_for(request).root / job.id / "runs").glob("*"))
            if len(runs) != 1:
                raise HTTPException(409, "The job has not started a model decision yet")
            directory = runs[0]
        else:
            directory = resolve(kind, reference, request)[2]
        return model_turn(directory, sequence)

    @application.get(
        "/api/experiments/{campaign_id}/cases/{key}/{leg}/model/{sequence}", response_model=ModelTurn
    )
    async def case_model_turn(
        campaign_id: str, key: str, leg: Literal["source", "followup"], sequence: int = PathParam(ge=0, le=70)
    ) -> ModelTurn:
        result, _ = case_for(campaign_id, key)
        evidence = result.source if leg == "source" else result.followup
        directory = (ROOT / evidence.run_path).resolve()
        if not directory.is_relative_to(ROOT / "artifacts/campaigns"):
            raise HTTPException(404, "Case evidence is outside the campaign registry")
        return model_turn(directory, sequence)

    original_openapi = application.openapi

    def openapi():
        schema = original_openapi()
        definitions = ClientContracts.model_json_schema()["$defs"]

        def references(value: object) -> object:
            if isinstance(value, dict):
                return {
                    key: item.replace("#/$defs/", "#/components/schemas/")
                    if key == "$ref" and isinstance(item, str)
                    else references(item)
                    for key, item in value.items()
                }
            if isinstance(value, list):
                return [references(item) for item in value]
            return value

        schema.setdefault("components", {}).setdefault("schemas", {}).update(references(definitions))
        return schema

    application.openapi = openapi  # type: ignore[method-assign]  # FastAPI's public custom-OpenAPI hook.
    return application


app = create_app()
