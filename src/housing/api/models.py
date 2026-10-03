from typing import Literal

from pydantic import JsonValue, field_validator, model_validator

from housing.contracts.common import FrozenModel, Mode, NonnegativeInt, Sha256, array_to_tuple
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.models import DatasetManifest
from housing.evaluation.models import CaseResult, HeadlineRow, MRId

type CaptureId = Literal["normal", "feedback", "empty"]
type EvidenceScope = Literal["analysis", "development_smoke", "auxiliary_index_omission", "pilot", "headline"]


class ErrorInfo(FrozenModel):
    code: str
    message: str
    stage: str


class Submission(FrozenModel):
    request: AnalysisRequest
    mode: Literal["live", "replay"]
    capture_id: CaptureId | None = None

    @model_validator(mode="after")
    def allowed_runtime(self) -> Submission:
        if self.request.seed not in (104729, 130363, 155921):
            raise ValueError("Choose one of the three frozen model seeds")
        if (self.mode == "replay") != (self.capture_id is not None):
            raise ValueError("Replay requires a capture ID; live analysis cannot consume a capture")
        return self


class Job(FrozenModel):
    id: str
    state: Literal["queued", "running", "completed", "failed"]
    created_at_utc: str
    updated_at_utc: str
    submission: Submission
    output: AnalysisOutput | None
    error: ErrorInfo | None


class CaptureSummary(FrozenModel):
    id: CaptureId
    title: str
    purpose: Literal["development_smoke", "auxiliary_index_omission"]
    request: AnalysisRequest
    model_decisions: NonnegativeInt
    description: str


class CatalogEntry(FrozenModel):
    id: MRId
    title: str
    family: str
    relation: str
    preconditions: tuple[str, ...]
    compared_fields: tuple[str, ...]
    tolerances: dict[str, str]
    witness: str


class Bootstrap(FrozenModel):
    default_request: AnalysisRequest
    captures: tuple[CaptureSummary, ...]
    dataset: DatasetManifest
    seed_values: tuple[int, ...]
    contract_version: Literal["1.0"]
    python_version: str
    fast_agent_version: str
    live_model_profile: str
    live_model_requirements: str
    mr_catalog: tuple[CatalogEntry, ...]


class PlotPoint(FrozenModel):
    x: str
    y: str | None


class AxisTick(FrozenModel):
    y: str
    label: str


class MonthView(FrozenModel):
    month: str
    label: str
    short_label: str
    observations: str
    price: str
    price_per_area: str
    price_mom: str
    price_yoy: str
    ppsf_mom: str
    count_mom: str
    price_plot: PlotPoint
    ppsf_plot: PlotPoint
    count_plot: PlotPoint
    support: Literal["empty", "sparse", "supported"]


class AnalysisView(FrozenModel):
    output: AnalysisOutput
    request: AnalysisRequest
    origin: Literal["live_capture", "live", "replay"]
    purpose: Literal["analysis", "development_smoke", "auxiliary_index_omission"]
    months: tuple[MonthView, ...]
    price_ticks: tuple[AxisTick, ...]
    ppsf_ticks: tuple[AxisTick, ...]
    count_ticks: tuple[AxisTick, ...]
    money_unit: str
    area_unit: str
    total_label: str
    window_change_label: str
    last_yoy_label: str
    csv_url: str
    json_url: str
    trace_url: str


class TraceEvent(FrozenModel):
    schema_version: Literal["1.0"]
    run_id: str
    sequence: NonnegativeInt
    timestamp_utc: str
    mode: Mode
    iteration: NonnegativeInt
    event: str
    actor: str
    parent_event_sequence: int | None
    query_sha256: Sha256
    dataset_view_sha256: Sha256
    plan_sha256: Sha256 | None
    payload: dict[str, JsonValue]
    payload_sha256: Sha256
    illustrative_fixture: bool


class WorkflowView(FrozenModel):
    run_id: str
    mode: Mode
    events: tuple[TraceEvent, ...]
    model_decisions: NonnegativeInt
    refinements: NonnegativeInt
    schema_repairs: NonnegativeInt
    query_unchanged: bool
    trace_url: str
    status: Literal["completed", "failed", "running"]
    failure: ErrorInfo | None
    evidence_scope: EvidenceScope


class ModelTurn(FrozenModel):
    sequence: NonnegativeInt
    input: dict[str, JsonValue]
    response: dict[str, JsonValue] | None
    dispatched: dict[str, JsonValue] | None
    budget: dict[str, JsonValue]


class HeadlineDisplay(HeadlineRow):
    base_rate_label: str
    ci95_label: str


class CampaignOverview(FrozenModel):
    id: str
    mode: Literal["live", "replay"]
    scope: Literal["pilot", "headline", "auxiliary"]
    expected_comparisons: NonnegativeInt
    completed_comparisons: NonnegativeInt
    state: Literal["running", "complete", "incomplete"]
    headlines: tuple[HeadlineDisplay, ...]
    last_case: str | None
    last_status: str | None
    seeds: tuple[int, ...]
    cohort_path: str


class ExperimentView(FrozenModel):
    campaigns: tuple[CampaignOverview, ...]


class CaseIndexItem(FrozenModel):
    key: str
    mr_id: str
    base_id: str
    seed: int
    status: str
    violation_kind: str | None
    source_reused: bool


class CaseDetail(FrozenModel):
    result: CaseResult
    source: AnalysisView | None
    followup: AnalysisView | None
    witness: dict[str, JsonValue]
    recipe: dict[str, JsonValue]


class ClientContracts(FrozenModel):
    """Schema-generation envelope; endpoints return these members directly."""

    bootstrap: Bootstrap
    submission: Submission
    job: Job
    analysis: AnalysisView
    workflow: WorkflowView
    model_turn: ModelTurn
    experiments: ExperimentView
    case_index: tuple[CaseIndexItem, ...]
    case_detail: CaseDetail
    error: ErrorInfo

    _arrays = field_validator("case_index", mode="before")(array_to_tuple)
