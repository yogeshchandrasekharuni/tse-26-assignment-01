"""Small explicit fixtures; their statistical expectations are hand calculated in tests."""

import csv
import io
from collections import Counter

from housing.contracts.common import Zip
from housing.contracts.request import AnalysisRequest
from housing.data.models import CSV_COLUMNS, DatasetManifest, Observation
from housing.data.store import Snapshot, ingest, logical_hash
from housing.identity import semantic_hash, sha256_bytes
from housing.tools.calendar import month_range


def observation(
    record_id: str,
    month: str,
    cents: int,
    sqft: int = 1,
    zip_code: Zip = "75001",
    listing_id: str = "same-listing",
) -> Observation:
    return Observation(
        record_id=record_id,
        listing_id=listing_id,
        month=month,
        zip=zip_code,
        property_type="condo",
        bedrooms=2,
        sqft=sqft,
        price_cents=cents,
    )


def csv_bytes(rows: tuple[Observation, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow(getattr(row, key) for key in CSV_COLUMNS)
    return stream.getvalue().encode()


def snapshot(
    rows: tuple[Observation, ...],
    start: str = "2024-10",
    end: str = "2026-09",
    zips: tuple[Zip, ...] = ("75001",),
) -> Snapshot:
    data = csv_bytes(rows)
    months = month_range(start, end)
    counts = Counter(row.month for row in rows)
    manifest = DatasetManifest(
        schema_version="1.0",
        dataset_id="hand-fixture",
        source_kind="synthetic_fixture",
        snapshot_path="fixture.csv",
        snapshot_sha256=sha256_bytes(data),
        logical_multiset_sha256=logical_hash(rows),
        expected_rows=len(rows),
        actual_rows=len(rows),
        valid_rows=len(rows),
        quarantined_rows=0,
        month_start=start,
        month_end=end,
        month_completeness={m: "complete" for m in months},
        partition_row_counts={m: counts[m] for m in months},
        unbucketed_rows=0,
        zips=zips,
        property_types=("condo",),
        row_schema_sha256=semantic_hash(Observation.model_json_schema()),
        generator=None,
        generated_at_utc="2026-09-24T18:30:00Z",
        data_license="Assignment test fixture",
        limitations=("Hand-constructed synthetic fixture",),
    )
    return ingest(data, manifest)


def request(
    *,
    compare: bool = False,
    zips: tuple[str, ...] = ("75001",),
    price_min: int | None = None,
    price_max: int | None = None,
) -> AnalysisRequest:
    return AnalysisRequest.model_validate(
        {
            "dataset_id": "hand-fixture",
            "window_end": "2026-09",
            "criteria": {
                "zips": zips,
                "property_types": ("condo",),
                "bedrooms_min": 1,
                "bedrooms_max": 5,
                "price_min_cents": price_min,
                "price_max_cents": price_max,
                "sqft_min": None,
                "sqft_max": None,
            },
            "display": {"money": "USD", "area": "SQFT"},
            "compare_regions": compare,
            "seed": 104729,
        }
    )
