from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from housing.contracts.common import (
    Decimal6,
    FrozenModel,
    Identifier,
    Mode,
    Month,
    NonnegativeInt,
    Seed,
    Sha256,
    Unsigned6,
    Zip,
    array_to_tuple,
)
from housing.tools.calendar import add_month, month_range


class Monthly(FrozenModel):
    month: Month
    listing_count: NonnegativeInt
    median_price_usd: Unsigned6 | None
    median_ppsf_usd: Unsigned6 | None
    price_mom_pct: Decimal6 | None
    ppsf_mom_pct: Decimal6 | None
    price_yoy_pct: Decimal6 | None
    ppsf_yoy_pct: Decimal6 | None
    count_mom_pct: Decimal6 | None

    @model_validator(mode="after")
    def empty_is_null(self) -> Monthly:
        levels = (self.median_price_usd, self.median_ppsf_usd)
        if self.listing_count == 0:
            if any(v is not None for v in levels):
                raise ValueError("Empty month must have null medians")
            if any(
                v is not None
                for v in (self.price_mom_pct, self.ppsf_mom_pct, self.price_yoy_pct, self.ppsf_yoy_pct)
            ):
                raise ValueError("Null medians cannot have defined price changes")
        elif any(v is None for v in levels):
            raise ValueError("Nonempty month requires both medians")
        return self


class ZipRanking(FrozenModel):
    zip: Zip
    median_ppsf_usd: Unsigned6 | None
    rank: Annotated[int, Field(ge=1)] | None

    @model_validator(mode="after")
    def no_data_no_rank(self) -> ZipRanking:
        if (self.median_ppsf_usd is None) != (self.rank is None):
            raise ValueError("No-data ZIP must have null median and rank")
        return self


class Summary(FrozenModel):
    window_price_change_pct: Decimal6 | None
    window_ppsf_change_pct: Decimal6 | None
    last_month_price_yoy_pct: Decimal6 | None
    last_month_ppsf_yoy_pct: Decimal6 | None
    total_observations: NonnegativeInt
    zip_rankings: Annotated[tuple[ZipRanking, ...], Field(max_length=12)]

    _rows = field_validator("zip_rankings", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def ordinal_ranks(self) -> Summary:
        if len({r.zip for r in self.zip_rankings}) != len(self.zip_rankings):
            raise ValueError("Duplicate ZIP in rankings")
        ranks = [r.rank for r in self.zip_rankings if r.rank is not None]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("Ranks must be ordinal and ordered")
        if any(r.rank is not None for r in self.zip_rankings[len(ranks) :]):
            raise ValueError("No-data ZIPs must sort last")
        return self


class Canonical(FrozenModel):
    window_start: Month
    window_end: Month
    monthly: Annotated[tuple[Monthly, ...], Field(min_length=12, max_length=12)]
    summary: Summary

    _rows = field_validator("monthly", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def consistent_window(self) -> Canonical:
        if self.window_start != add_month(self.window_end, -11):
            raise ValueError("A visible window must contain twelve calendar months")
        if tuple(r.month for r in self.monthly) != month_range(self.window_start, self.window_end):
            raise ValueError("Monthly rows must be unique, contiguous and oldest first")
        if self.summary.total_observations != sum(r.listing_count for r in self.monthly):
            raise ValueError("Total must sum observation counts")
        last = self.monthly[-1]
        if (self.summary.last_month_price_yoy_pct, self.summary.last_month_ppsf_yoy_pct) != (
            last.price_yoy_pct,
            last.ppsf_yoy_pct,
        ):
            raise ValueError("Summary YoY must equal the final monthly YoY")
        return self


class PresentedMonth(FrozenModel):
    month: Month
    median_price: Unsigned6 | None
    median_price_per_area: Unsigned6 | None


class Presentation(FrozenModel):
    money: Literal["USD", "USD_THOUSANDS"]
    area: Literal["SQFT", "SQM"]
    monthly: Annotated[tuple[PresentedMonth, ...], Field(min_length=12, max_length=12)]

    _rows = field_validator("monthly", mode="before")(array_to_tuple)


class Quality(FrozenModel):
    status: Literal["complete", "limited"]
    codes: tuple[str, ...]
    sparse_months: tuple[Month, ...]

    _arrays = field_validator("codes", "sparse_months", mode="before")(array_to_tuple)


class Narrative(FrozenModel):
    fact_ids: tuple[str, ...]
    caveat_codes: tuple[str, ...]
    text: str

    _arrays = field_validator("fact_ids", "caveat_codes", mode="before")(array_to_tuple)


class Metadata(FrozenModel):
    run_id: Identifier
    dataset_id: Identifier
    snapshot_sha256: Sha256
    dataset_view_sha256: Sha256
    logical_multiset_sha256: Sha256
    query_sha256: Sha256
    contract_version: Literal["1.0"]
    mode: Mode
    model_profile: str
    requested_seed: Seed
    effective_seed: Seed | None
    seed_support: Literal["verified_model_default", "best_effort", "unsupported", "replay_recorded"]
    prompt_bundle_sha256: Sha256
    trace_path: str
    live_campaign_id: str | None


class AnalysisOutput(FrozenModel):
    status: Literal["completed"]
    canonical: Canonical
    presentation: Presentation
    quality: Quality
    narrative: Narrative
    metadata: Metadata

    @model_validator(mode="after")
    def matching_presentation_window(self) -> AnalysisOutput:
        if tuple(r.month for r in self.presentation.monthly) != tuple(
            r.month for r in self.canonical.monthly
        ):
            raise ValueError("Presentation must match canonical month labels")
        return self
