from typing import Literal

from pydantic import JsonValue, field_validator

from housing.contracts.common import FrozenModel, NonnegativeInt, Sha256, array_to_tuple
from housing.contracts.errors import ErrorCode
from housing.contracts.request import AnalysisRequest

type MRId = Literal["MR01", "MR02", "MR03", "MR04", "MR05", "MR06", "MR07", "MR08", "MR09", "MR10"]
MRS: tuple[MRId, ...] = ("MR01", "MR02", "MR03", "MR04", "MR05", "MR06", "MR07", "MR08", "MR09", "MR10")
SEEDS = (104729, 130363, 155921)


class Recipe(FrozenModel):
    version: Literal["transform-1"]
    mr: MRId
    transform_seed: NonnegativeInt
    target_month: str | None = None
    excluded_zip: str | None = None
    factor_numerator: int = 5
    factor_denominator: int = 4
    delta_cents: int = 100000


class Eligibility(FrozenModel):
    eligible: bool
    reasons: tuple[str, ...]
    witnesses: dict[str, JsonValue]

    _arrays = field_validator("reasons", mode="before")(array_to_tuple)


class CaseSpec(FrozenModel):
    mr: MRId
    base_id: str
    slice_group: str
    base_query_sha256: Sha256
    source_request: AnalysisRequest
    followup_request: AnalysisRequest
    source_view_sha256: Sha256
    followup_view_sha256: Sha256
    recipe: Recipe
    eligibility: Eligibility


class Cohort(FrozenModel):
    version: Literal["cohort-1"]
    frozen_at_utc: str
    candidate_recipe: str
    source_snapshot_sha256: Sha256
    evaluation_inputs: dict[str, Sha256]
    seeds: tuple[int, ...]
    cases: tuple[CaseSpec, ...]
    invalid_candidates: tuple[CaseSpec, ...]
    coverage: dict[str, JsonValue]

    _arrays = field_validator("seeds", "cases", "invalid_candidates", mode="before")(array_to_tuple)


class Difference(FrozenModel):
    path: str
    rule: str
    source: JsonValue
    followup: JsonValue
    expected: JsonValue
    absolute_error: str | None = None
    tolerance: str | None = None


class Comparison(FrozenModel):
    status: Literal["pass", "violation"]
    compared_numeric_count: NonnegativeInt
    max_absolute_error: str
    differences: tuple[Difference, ...]

    _arrays = field_validator("differences", mode="before")(array_to_tuple)


class LegOutcome(FrozenModel):
    execution_key: Sha256
    status: Literal["completed", "failed"]
    run_id: str
    run_path: str
    capture_path: str | None
    request_sha256: Sha256
    view_sha256: Sha256
    requested_seed: int
    effective_seed: int | None
    canonical_sha256: Sha256 | None
    output_sha256: Sha256 | None
    error_code: ErrorCode | None
    error_stage: str | None
    duration_ns: NonnegativeInt


class CaseResult(FrozenModel):
    schema_version: Literal["case-2"]
    campaign_id: str
    live_campaign_id: str
    mode: Literal["live", "replay"]
    mr_id: MRId
    mr_version: Literal["1.0"]
    base_id: str
    slice_group: str
    base_semantic_sha256: Sha256
    cohort_case_sha256: Sha256
    transform_sha256: Sha256
    seed: int
    eligibility_path: str
    source: LegOutcome
    followup: LegOutcome
    source_reused_from: str | None
    status: Literal["pass", "violation", "execution_error"]
    violation_kind: Literal["relation", "output_contract"] | None
    reason_codes: tuple[ErrorCode, ...]
    comparison: Comparison | None

    _arrays = field_validator("reason_codes", mode="before")(array_to_tuple)


class HeadlineRow(FrozenModel):
    schema_version: Literal["headline-2"]
    mr_id: MRId
    family: Literal["invariance", "monotonic", "directional"]
    mode: Literal["live", "replay"]
    campaign_id: str
    live_campaign_id: str
    eligible_bases: NonnegativeInt
    completed_bases: NonnegativeInt
    violating_bases: NonnegativeInt
    base_rate: str | None
    ci_method: Literal["wilson_score"]
    ci_unit: Literal["distinct_completed_eligible_base"]
    ci95_low: str | None
    ci95_high: str | None
    seed_values: tuple[int, ...]
    seed_pair_violations: NonnegativeInt
    seed_pairs_completed: NonnegativeInt
    invalid_candidates: NonnegativeInt
    execution_errors: NonnegativeInt
    output_contract_violations: NonnegativeInt
    complete: bool
    interpretation: str

    _arrays = field_validator("seed_values", mode="before")(array_to_tuple)
