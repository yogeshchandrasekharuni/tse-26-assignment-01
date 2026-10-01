"""Exact tool results and their trusted workflow bindings."""

from fractions import Fraction
from math import gcd
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from housing.contracts.common import (
    FrozenModel,
    Identifier,
    Month,
    NonnegativeInt,
    PartitionOrder,
    PositiveInt,
    RegionPurpose,
    Sha256,
    Specialist,
    Strategy,
    Zip,
    array_to_tuple,
)
from housing.identity import semantic_hash


class Rational(FrozenModel):
    numerator: int
    denominator: PositiveInt

    @model_validator(mode="after")
    def reduced(self) -> Rational:
        if gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("Exact rationals must be reduced with positive denominator")
        return self

    @classmethod
    def of(cls, value: Fraction | int) -> Rational:
        value = Fraction(value)
        return cls(numerator=value.numerator, denominator=value.denominator)

    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)


class ExactMonth(FrozenModel):
    month: Month
    available: bool
    count: NonnegativeInt | None
    median_price_usd: Rational | None
    median_ppsf_usd: Rational | None

    @model_validator(mode="after")
    def availability(self) -> ExactMonth:
        if not self.available:
            if any(v is not None for v in (self.count, self.median_price_usd, self.median_ppsf_usd)):
                raise ValueError("Unavailable lookback must have null count and medians")
        elif self.count is None:
            raise ValueError("Available month must have a count")
        elif (self.count > 0) != (self.median_price_usd is not None and self.median_ppsf_usd is not None):
            raise ValueError("Only nonempty months have medians")
        elif self.count == 0 and (self.median_price_usd is not None or self.median_ppsf_usd is not None):
            raise ValueError("Empty month must have both medians null")
        return self


class CountMonth(FrozenModel):
    month: Month
    available: bool
    count: NonnegativeInt | None

    @model_validator(mode="after")
    def availability(self) -> CountMonth:
        if self.available != (self.count is not None):
            raise ValueError("Only available months have a count, including zero")
        return self


class ExactZip(FrozenModel):
    zip: Zip
    count: NonnegativeInt
    median_ppsf_usd: Rational | None

    @model_validator(mode="after")
    def count_and_median(self) -> ExactZip:
        if (self.count > 0) != (self.median_ppsf_usd is not None):
            raise ValueError("Only nonempty ZIPs have a pooled median")
        return self


class PriceResult(FrozenModel):
    tool: Literal["price_stats"]
    monthly: Annotated[tuple[ExactMonth, ...], Field(min_length=24, max_length=24)]

    _arrays = field_validator("monthly", mode="before")(array_to_tuple)


class SupplyResult(FrozenModel):
    tool: Literal["supply_stats"]
    monthly: Annotated[tuple[CountMonth, ...], Field(min_length=24, max_length=24)]

    _arrays = field_validator("monthly", mode="before")(array_to_tuple)


class RegionResult(FrozenModel):
    tool: Literal["region_stats"]
    purpose: Literal["public_comparison", "coverage_diagnostic"]
    pooled: tuple[ExactZip, ...]
    counts: tuple[CountMonth, ...]

    _arrays = field_validator("pooled", "counts", mode="before")(array_to_tuple)


type StatsResult = PriceResult | SupplyResult | RegionResult


class WorkflowPlan(FrozenModel):
    version: Annotated[int, Field(ge=0, le=2)]
    canonical_query_sha256: Sha256
    dataset_view_sha256: Sha256
    visible_months: Annotated[tuple[Month, ...], Field(min_length=12, max_length=12)]
    required_months: Annotated[tuple[Month, ...], Field(min_length=24, max_length=24)]
    scan_strategy: Strategy
    active_specialists: tuple[Specialist, ...]
    region_purpose: RegionPurpose
    trigger_review_event_sequence: NonnegativeInt | None
    planner_decision_sha256: Sha256

    _arrays = field_validator("visible_months", "required_months", "active_specialists", mode="before")(
        array_to_tuple
    )

    @property
    def semantic_sha256(self) -> str:
        return semantic_hash(self.model_dump(mode="json", exclude={"trigger_review_event_sequence"}))


class ToolReceipt(FrozenModel):
    schema_version: Literal["1.0"]
    receipt_id: Identifier
    tool: Literal["price_stats", "supply_stats", "region_stats"]
    tool_version: Literal["1.0"]
    run_id: Identifier
    iteration: Annotated[int, Field(ge=0, le=2)]
    plan_sha256: Sha256
    canonical_query_sha256: Sha256
    dataset_view_sha256: Sha256
    selection_sha256: Sha256
    strategy: Strategy
    source_snapshot_complete: bool
    scan_complete: bool
    visible_months: tuple[Month, ...]
    unavailable_lookback_months: tuple[Month, ...]
    partition_receipts_path: str
    result_path: str
    result_sha256: Sha256
    decision_sha256: Sha256
    duration_ms: NonnegativeInt

    _arrays = field_validator("visible_months", "unavailable_lookback_months", mode="before")(array_to_tuple)

    @property
    def semantic_sha256(self) -> str:
        return semantic_hash(
            self.model_dump(
                mode="json",
                exclude={
                    "receipt_id",
                    "run_id",
                    "partition_receipts_path",
                    "result_path",
                    "duration_ms",
                },
            )
        )


class PartitionReceipt(FrozenModel):
    month: Month
    zip: Zip
    available: bool
    index_present: bool
    selected_count: NonnegativeInt | None
    selected_record_ids_sha256: Sha256
    execution_order: PartitionOrder


class ToolExecution(FrozenModel):
    receipt: ToolReceipt
    result: StatsResult

    @model_validator(mode="after")
    def result_integrity(self) -> ToolExecution:
        if self.receipt.tool != self.result.tool or self.receipt.result_sha256 != semantic_hash(self.result):
            raise ValueError("Tool receipt does not bind the supplied result")
        return self
