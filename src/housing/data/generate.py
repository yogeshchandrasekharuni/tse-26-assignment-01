"""Deterministic assignment recipe. A frozen version is compared, never overwritten."""

import csv
import io
import json
import platform
import random
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from housing.contracts.common import (
    FrozenModel,
    Identifier,
    Month,
    PositiveInt,
    PropertyType,
    Seed,
    Zip,
    array_to_tuple,
)
from housing.data.models import CSV_COLUMNS, DatasetManifest, GeneratorProvenance, Observation
from housing.data.store import ingest, logical_hash
from housing.identity import ROOT, canonical_json, semantic_hash, sha256_bytes, write_json
from housing.tools.calendar import month_range
from housing.tools.exact import round_half_even

CONFIG_PATH = ROOT / "configs/generator.json"
CSV_PATH = ROOT / "data/frozen/dallas-synth-v1.csv"
MANIFEST_PATH = ROOT / "data/manifests/dallas-synth-v1.json"
SCHEMA_PATH = ROOT / "data/observation.schema.json"


class GeneratorConfig(FrozenModel):
    schema_version: Literal["1.0"]
    dataset_id: Identifier
    month_start: Month
    month_end: Month
    zips: tuple[Zip, ...]
    property_types: tuple[PropertyType, ...]
    observations_per_zip_month: PositiveInt
    expected_rows: PositiveInt
    generator_seed: Seed
    python_version: str
    prng: str
    seasonal_bp: Annotated[tuple[int, ...], Field(min_length=12, max_length=12)]
    monthly_trend_bp: int
    price_rounding: Literal["exact half-even to nearest 100 cents"]
    recipe_document: str
    claim: str

    _arrays = field_validator("zips", "property_types", "seasonal_bp", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def recipe_consistency(self) -> GeneratorConfig:
        n = (
            len(month_range(self.month_start, self.month_end))
            * len(self.zips)
            * self.observations_per_zip_month
        )
        if n != self.expected_rows:
            raise ValueError("Expected rows do not match recipe dimensions")
        if self.property_types != ("single_family", "condo", "townhouse"):
            raise ValueError("This recipe requires the three types in their specified slot order")
        return self


def generate(config: GeneratorConfig) -> tuple[Observation, ...]:
    if platform.python_version() != config.python_version:
        raise RuntimeError(
            f"Generator requires Python {config.python_version}; found {platform.python_version()}"
        )
    rng = random.Random(config.generator_seed)
    rows: list[Observation] = []
    offsets = {"single_family": 0, "condo": 1500, "townhouse": 750}
    for t, month in enumerate(month_range(config.month_start, config.month_end)):
        trend_bp = 10000 + config.monthly_trend_bp * t + config.seasonal_bp[t % 12]
        for z, zip_code in enumerate(config.zips):
            for i in range(config.observations_per_zip_month):
                property_type = config.property_types[i % 3]
                bedrooms = 1 + i % 5
                sqft = 650 + 380 * bedrooms + 30 * (z % 4) + rng.randint(-120, 120)
                ppsf_cents = 13500 + 850 * z + offsets[property_type] + rng.randint(-1800, 1800)
                price_cents = 100 * round_half_even(Fraction(sqft * ppsf_cents * trend_bp, 1_000_000))
                if not 500 <= sqft <= 5000 or not 8_000_000 <= price_cents <= 200_000_000:
                    raise RuntimeError("Generated row is outside the declared recipe support")
                rows.append(
                    Observation(
                        record_id=f"obs-{t:02d}-{z:02d}-{i:03d}",
                        listing_id=f"listing-{z:02d}-{i:03d}",
                        month=month,
                        zip=zip_code,
                        property_type=property_type,
                        bedrooms=bedrooms,
                        sqft=sqft,
                        price_cents=price_cents,
                    )
                )
    if len(rows) != config.expected_rows:
        raise RuntimeError("Generated row count differs from recipe")
    return tuple(rows)


def encode_csv(rows: tuple[Observation, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow(getattr(row, column) for column in CSV_COLUMNS)
    return stream.getvalue().encode("utf-8")


def build_manifest(
    config: GeneratorConfig, rows: tuple[Observation, ...], data: bytes, generated_at: str
) -> DatasetManifest:
    counts = Counter(row.month for row in rows)
    months = month_range(config.month_start, config.month_end)
    generator_path = Path(__file__).resolve()
    dependencies = (
        "src/housing/tools/exact.py",
        "src/housing/tools/calendar.py",
        "src/housing/data/models.py",
        "src/housing/contracts/common.py",
    )
    return DatasetManifest(
        schema_version="1.0",
        dataset_id=config.dataset_id,
        source_kind="synthetic",
        snapshot_path=str(CSV_PATH.relative_to(ROOT)),
        snapshot_sha256=sha256_bytes(data),
        logical_multiset_sha256=logical_hash(rows),
        expected_rows=config.expected_rows,
        actual_rows=len(rows),
        valid_rows=len(rows),
        quarantined_rows=0,
        month_start=config.month_start,
        month_end=config.month_end,
        month_completeness={m: "complete" for m in months},
        partition_row_counts={m: counts[m] for m in months},
        unbucketed_rows=0,
        zips=config.zips,
        property_types=config.property_types,
        row_schema_sha256=semantic_hash(Observation.model_json_schema()),
        generator=GeneratorProvenance(
            path=str(generator_path.relative_to(ROOT)),
            sha256=sha256_bytes(generator_path.read_bytes()),
            config_path=str(CONFIG_PATH.relative_to(ROOT)),
            config_sha256=sha256_bytes(CONFIG_PATH.read_bytes()),
            dependency_sha256={p: sha256_bytes((ROOT / p).read_bytes()) for p in dependencies},
            seed=config.generator_seed,
            python_version=platform.python_version(),
            algorithm=config.prng,
        ),
        generated_at_utc=generated_at,
        data_license="CC0-1.0 (generated synthetic observations only)",
        limitations=(
            "Synthetic software test feed, not measured Dallas market data",
            "Fixed inventory of 120 observations per ZIP per month; repeated listing IDs",
            "Chosen ZIP subset and designed trend, seasonality, composition and noise",
            "No addresses, seller behavior or missingness in the clean snapshot",
            "Relational consistency on this feed does not establish market realism",
        ),
    )


def freeze() -> DatasetManifest:
    from datetime import UTC, datetime

    config = GeneratorConfig.model_validate_json(CONFIG_PATH.read_bytes())
    rows = generate(config)
    data = encode_csv(rows)
    if encode_csv(generate(config)) != data:
        raise RuntimeError("Independent regeneration was not byte-identical")
    if CSV_PATH.exists() != MANIFEST_PATH.exists():
        raise RuntimeError("Partial frozen dataset exists; inspect it before generating a new version")
    existing = (
        DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes()) if MANIFEST_PATH.exists() else None
    )
    created = existing.generated_at_utc if existing else datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = build_manifest(config, rows, data, created)
    ingest(data, manifest)
    if existing:
        if CSV_PATH.read_bytes() != data or canonical_json(existing) != canonical_json(manifest):
            raise RuntimeError("Frozen v1 differs from regeneration/provenance; create a new dataset version")
        if not SCHEMA_PATH.exists() or semantic_hash(Observation.model_json_schema()) != semantic_hash(
            json.loads(SCHEMA_PATH.read_bytes())
        ):
            raise RuntimeError("Frozen row schema differs from the current contract")
    else:
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        CSV_PATH.write_bytes(data)
        write_json(SCHEMA_PATH, Observation.model_json_schema())
        write_json(MANIFEST_PATH, manifest)
    return manifest


if __name__ == "__main__":
    manifest = freeze()
    print(
        canonical_json(
            {
                "dataset_id": manifest.dataset_id,
                "rows": manifest.actual_rows,
                "sha256": manifest.snapshot_sha256,
                "status": "frozen_bytes_verified_twice",
            }
        )
    )
