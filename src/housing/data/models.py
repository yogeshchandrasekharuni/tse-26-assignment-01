from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from housing.contracts.common import (
    FrozenModel,
    Identifier,
    Month,
    NonnegativeInt,
    PositiveInt,
    PropertyType,
    Sha256,
    Zip,
    array_to_tuple,
)
from housing.tools.calendar import month_range

CSV_COLUMNS = ("record_id", "listing_id", "month", "zip", "property_type", "bedrooms", "sqft", "price_cents")


class Observation(FrozenModel):
    record_id: Identifier
    listing_id: Identifier
    month: Month
    zip: Zip
    property_type: PropertyType
    bedrooms: Annotated[int, Field(ge=1, le=5)]
    sqft: PositiveInt
    price_cents: PositiveInt


class QuarantinedRow(FrozenModel):
    line: PositiveInt
    record_id: str | None
    reason: str
    raw_hash: Sha256


class GeneratorProvenance(FrozenModel):
    path: str
    sha256: Sha256
    config_path: str
    config_sha256: Sha256
    dependency_sha256: dict[str, Sha256]
    seed: NonnegativeInt
    python_version: str
    algorithm: str


class DatasetManifest(FrozenModel):
    schema_version: Literal["1.0"]
    dataset_id: Identifier
    source_kind: Literal["synthetic", "synthetic_fixture", "transformed"]
    snapshot_path: str
    snapshot_sha256: Sha256
    logical_multiset_sha256: Sha256
    expected_rows: NonnegativeInt
    actual_rows: NonnegativeInt
    valid_rows: NonnegativeInt
    quarantined_rows: NonnegativeInt
    month_start: Month
    month_end: Month
    month_completeness: dict[str, Literal["complete", "incomplete"]]
    partition_row_counts: dict[str, NonnegativeInt]
    unbucketed_rows: NonnegativeInt
    zips: tuple[Zip, ...]
    property_types: tuple[PropertyType, ...]
    row_schema_sha256: Sha256
    generator: GeneratorProvenance | None
    generated_at_utc: str
    data_license: str
    limitations: tuple[str, ...]

    _arrays = field_validator("zips", "property_types", "limitations", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def accounted_rows(self) -> DatasetManifest:
        if self.expected_rows != self.actual_rows:
            raise ValueError("Manifest raw row count does not meet declared expectation")
        if self.actual_rows != self.valid_rows + self.quarantined_rows:
            raise ValueError("Valid/quarantined counts must account for every raw row")
        months = set(month_range(self.month_start, self.month_end))
        if not set(self.month_completeness).issubset(months):
            raise ValueError("Completeness map has months outside the declared source range")
        if set(self.partition_row_counts) != months:
            raise ValueError(
                "Every source month needs an explicit raw count, including complete empty months"
            )
        if sum(self.partition_row_counts.values()) + self.unbucketed_rows != self.actual_rows:
            raise ValueError("Partition and unbucketed counts must sum to raw rows")
        if not self.zips or not self.property_types or len(set(self.zips)) != len(self.zips):
            raise ValueError("Dataset vocabulary must be nonempty with unique ZIPs")
        return self
