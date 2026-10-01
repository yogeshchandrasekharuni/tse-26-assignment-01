"""Shared boundary primitives; requests and results contain no mutable collections."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ZIPS = (
    "75001",
    "75006",
    "75019",
    "75024",
    "75034",
    "75038",
    "75063",
    "75080",
    "75093",
    "75201",
    "75204",
    "75214",
)
PROPERTY_TYPES = ("single_family", "condo", "townhouse")
type Zip = Literal[
    "75001", "75006", "75019", "75024", "75034", "75038", "75063", "75080", "75093", "75201", "75204", "75214"
]
type PropertyType = Literal["single_family", "condo", "townhouse"]
type Strategy = Literal["indexed", "full_csv", "rebuilt_index"]
type Specialist = Literal["price", "supply", "region"]
type PartitionOrder = Literal["month_asc", "zip_asc"]
type RegionPurpose = Literal["none", "public_comparison", "coverage_diagnostic"]
type Signal = Literal[
    "INDEX_COVERAGE_MISMATCH",
    "SPARSE_SLICE",
    "RECEIPT_MISMATCH",
    "COMPLETE_SUPPORT",
    "CONFIRMED_SPARSE",
    "UNRECOVERABLE_INTEGRITY",
]
type Action = Literal["INITIAL", "EXACT_RESCAN_WITH_REGION", "REBUILD_INDEX_AND_RESCAN"]
type Mode = Literal["live", "replay", "policy_simulation"]
type Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]+$", min_length=1)]
type Month = Annotated[str, Field(pattern=r"^(?!0000)\d{4}-(0[1-9]|1[0-2])$")]
type Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
type Unsigned6 = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)\.[0-9]{6}$")]
type Decimal6 = Annotated[str, Field(pattern=r"^(?!-0\.000000$)-?(0|[1-9][0-9]*)\.[0-9]{6}$")]
type NonnegativeInt = Annotated[int, Field(ge=0)]
type PositiveInt = Annotated[int, Field(ge=1)]
type Seed = Annotated[int, Field(ge=0, le=2147483647)]


class FrozenModel(BaseModel):
    # Calendar and negative-zero constraints use lookahead, unsupported by Rust's regex engine.
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, regex_engine="python-re")


def array_to_tuple(value: object) -> object:
    """Normalize JSON arrays while refusing string/number/boolean coercion."""
    return tuple(value) if isinstance(value, list) else value


def normalized_set(value: object) -> object:
    if isinstance(value, (tuple, list)):
        if not all(isinstance(item, str) for item in value):
            raise ValueError("Set members must be strings")
        return tuple(sorted(set(value)))
    return value
