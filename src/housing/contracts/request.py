from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from housing.contracts.common import (
    FrozenModel,
    Identifier,
    Month,
    NonnegativeInt,
    PositiveInt,
    PropertyType,
    Seed,
    Zip,
    normalized_set,
)
from housing.tools.calendar import add_month, month_range


class Criteria(FrozenModel):
    zips: Annotated[tuple[Zip, ...], Field(min_length=1)]
    property_types: Annotated[tuple[PropertyType, ...], Field(min_length=1)]
    bedrooms_min: Annotated[int, Field(ge=1, le=5)]
    bedrooms_max: Annotated[int, Field(ge=1, le=5)]
    price_min_cents: NonnegativeInt | None
    price_max_cents: NonnegativeInt | None
    sqft_min: PositiveInt | None
    sqft_max: PositiveInt | None

    _sets = field_validator("zips", "property_types", mode="before")(normalized_set)

    @model_validator(mode="after")
    def ordered_bounds(self) -> Criteria:
        for low, high in [
            (self.bedrooms_min, self.bedrooms_max),
            (self.price_min_cents, self.price_max_cents),
            (self.sqft_min, self.sqft_max),
        ]:
            if low is not None and high is not None and low > high:
                raise ValueError("Lower bound exceeds upper bound")
        return self


class Display(FrozenModel):
    money: Literal["USD", "USD_THOUSANDS"]
    area: Literal["SQFT", "SQM"]


class AnalysisRequest(FrozenModel):
    dataset_id: Identifier
    window_end: Month
    criteria: Criteria
    display: Display
    compare_regions: bool
    seed: Seed

    @field_validator("window_end")
    @classmethod
    def valid_lookback_calendar(cls, value: str) -> str:
        add_month(value, -23)
        return value

    @property
    def visible_months(self) -> tuple[str, ...]:
        return month_range(add_month(self.window_end, -11), self.window_end)

    @property
    def required_months(self) -> tuple[str, ...]:
        return month_range(add_month(self.window_end, -23), self.window_end)

    def housing_query(self, view_sha256: str) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_view_sha256": view_sha256,
            "window_end": self.window_end,
            "criteria": self.criteria.model_dump(mode="json"),
            "compare_regions": self.compare_regions,
        }
