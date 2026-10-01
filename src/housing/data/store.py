"""Strict raw ingestion and immutable indexed/full-CSV views."""

import csv
import io
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from pydantic import ValidationError

from housing.contracts.common import Strategy
from housing.contracts.errors import HousingError
from housing.contracts.request import AnalysisRequest
from housing.data.models import CSV_COLUMNS, DatasetManifest, Observation, QuarantinedRow
from housing.identity import canonical_json, semantic_hash, sha256_bytes
from housing.tools.calendar import month_range


@dataclass(frozen=True)
class ParsedCSV:
    rows: tuple[Observation, ...]
    quarantine: tuple[QuarantinedRow, ...]
    raw_count: int
    month_counts: Mapping[str, int]
    unbucketed_count: int


def parse_csv(data: bytes) -> ParsedCSV:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HousingError("DATA_INVALID", "CSV must be UTF-8") from error
    if text.startswith("\ufeff"):
        raise HousingError("DATA_INVALID", "CSV must not contain a BOM")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    try:
        fields = tuple(reader.fieldnames or ())
    except csv.Error as error:
        raise HousingError("DATA_INVALID", "Malformed CSV header") from error
    if fields != CSV_COLUMNS:
        raise HousingError("DATA_INVALID", "CSV header/order must match the observation contract")
    rows: list[Observation] = []
    quarantine: list[QuarantinedRow] = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    raw_count = unbucketed = 0
    try:
        for line in reader:
            raw_count += 1
            record_id = line.get("record_id")
            if record_id:
                if record_id in seen:
                    raise HousingError(
                        "DATA_INVALID", f"Duplicate record_id at line {reader.line_num}: {record_id}"
                    )
                seen.add(record_id)
            month = line.get("month")
            if month and re.fullmatch(r"(?!0000)\d{4}-(0[1-9]|1[0-2])", month):
                counts[month] += 1
            else:
                unbucketed += 1
            try:
                if None in line or any(v is None for v in line.values()):
                    raise ValueError("Wrong field count")
                converted: dict[str, object] = dict(line)
                for key in ("bedrooms", "sqft", "price_cents"):
                    value = line[key]
                    if not isinstance(value, str) or not re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
                        raise ValueError(f"{key} must be canonical base-10 integer text")
                    converted[key] = int(value)
                rows.append(Observation.model_validate(converted))
            except (ValidationError, ValueError) as error:
                reason = (
                    "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['type']}" for item in error.errors())
                    if isinstance(error, ValidationError)
                    else str(error)
                )
                # CSV rows cannot carry a null dict key into canonical JSON; preserve it as a pair list.
                raw_hash = semantic_hash([(key, value) for key, value in line.items()])
                quarantine.append(
                    QuarantinedRow(
                        line=reader.line_num, record_id=record_id, reason=reason, raw_hash=raw_hash
                    )
                )
    except csv.Error as error:
        raise HousingError("DATA_INVALID", f"Malformed CSV at line {reader.line_num}") from error
    return ParsedCSV(tuple(rows), tuple(quarantine), raw_count, MappingProxyType(dict(counts)), unbucketed)


def logical_hash(rows: tuple[Observation, ...]) -> str:
    # A multiset of full row representations; equal business listing labels are not deduplicated.
    return semantic_hash(sorted(canonical_json(row) for row in rows))


@dataclass(frozen=True)
class Snapshot:
    dataset_id: str
    source_sha256: str
    view_sha256: str
    logical_multiset_sha256: str
    rows: tuple[Observation, ...]
    months: tuple[str, ...]
    zips: tuple[str, ...]
    index: Mapping[tuple[str, str], tuple[Observation, ...]]
    index_sha256: str
    quarantine: tuple[QuarantinedRow, ...]
    raw_csv: bytes

    def omit_index_partitions(self, omissions: frozenset[tuple[str, str]]) -> Snapshot:
        """Labeled control: raw source remains intact, but index partition keys are absent."""
        from dataclasses import replace

        index = {k: v for k, v in self.index.items() if k not in omissions}
        return replace(self, index=MappingProxyType(index), index_sha256=index_hash(self.view_sha256, index))


def index_hash(view_sha256: str, index: Mapping[tuple[str, str], tuple[Observation, ...]]) -> str:
    return semantic_hash(
        {
            "view": view_sha256,
            "partitions": [
                [month, zip_code, sorted(row.record_id for row in rows)]
                for (month, zip_code), rows in sorted(index.items())
            ],
        }
    )


def ingest(data: bytes, manifest: DatasetManifest, *, source_sha256: str | None = None) -> Snapshot:
    if semantic_hash(Observation.model_json_schema()) != manifest.row_schema_sha256:
        raise HousingError("DATA_INVALID", "Manifest row schema differs from this contract")
    if sha256_bytes(data) != manifest.snapshot_sha256:
        raise HousingError("DATA_INVALID", "CSV byte hash differs from its manifest")
    months = month_range(manifest.month_start, manifest.month_end)
    if any(manifest.month_completeness.get(month) != "complete" for month in months):
        raise HousingError("DATA_INCOMPLETE", "Source snapshot has missing/incomplete month declarations")
    parsed = parse_csv(data)
    if (
        parsed.raw_count != manifest.actual_rows
        or len(parsed.rows) != manifest.valid_rows
        or (len(parsed.quarantine) != manifest.quarantined_rows)
    ):
        raise HousingError("DATA_INVALID", "Parsed row/quarantine counts differ from manifest")
    actual_counts = {month: parsed.month_counts.get(month, 0) for month in months}
    if (
        set(parsed.month_counts) - set(months)
        or actual_counts != manifest.partition_row_counts
        or parsed.unbucketed_count != manifest.unbucketed_rows
    ):
        raise HousingError("DATA_INCOMPLETE", "Source partition row counts differ from manifest")
    logical = logical_hash(parsed.rows)
    if logical != manifest.logical_multiset_sha256:
        raise HousingError("DATA_INVALID", "Logical row multiset hash differs from manifest")
    partitions: dict[tuple[str, str], list[Observation]] = {(m, z): [] for m in months for z in manifest.zips}
    for row in parsed.rows:
        if row.zip not in manifest.zips or row.property_type not in manifest.property_types:
            raise HousingError("DATA_INVALID", "Valid row is outside the manifest vocabulary")
        partitions[row.month, row.zip].append(row)
    index = MappingProxyType({key: tuple(value) for key, value in partitions.items()})
    return Snapshot(
        manifest.dataset_id,
        source_sha256 or manifest.snapshot_sha256,
        manifest.snapshot_sha256,
        logical,
        parsed.rows,
        months,
        manifest.zips,
        index,
        index_hash(manifest.snapshot_sha256, index),
        parsed.quarantine,
        data,
    )


def load_snapshot(csv_path: Path, manifest_path: Path) -> Snapshot:
    try:
        manifest = DatasetManifest.model_validate_json(manifest_path.read_bytes())
        return ingest(csv_path.read_bytes(), manifest)
    except (OSError, ValidationError) as error:
        raise HousingError("DATA_INVALID", f"Snapshot/manifest could not be loaded: {error}") from error


def matches(row: Observation, request: AnalysisRequest) -> bool:
    c = request.criteria
    return (
        row.zip in c.zips
        and row.property_type in c.property_types
        and c.bedrooms_min <= row.bedrooms <= c.bedrooms_max
        and (c.sqft_min is None or row.sqft >= c.sqft_min)
        and (c.sqft_max is None or row.sqft <= c.sqft_max)
        and (c.price_min_cents is None or row.price_cents >= c.price_min_cents)
        and (c.price_max_cents is None or row.price_cents <= c.price_max_cents)
    )


@dataclass(frozen=True)
class Selection:
    snapshot: Snapshot
    request: AnalysisRequest
    strategy: Strategy
    rows: tuple[Observation, ...]
    available_months: tuple[str, ...]
    missing_index_partitions: tuple[tuple[str, str], ...]
    selection_sha256: str
    query_sha256: str

    @property
    def scan_complete(self) -> bool:
        return not self.missing_index_partitions

    def ordered_rows(self, order: str) -> tuple[Observation, ...]:
        if order == "month_asc":
            return tuple(sorted(self.rows, key=lambda r: (r.month, r.zip, r.record_id)))
        if order == "zip_asc":
            return tuple(sorted(self.rows, key=lambda r: (r.zip, r.month, r.record_id)))
        raise HousingError("AGENT_POLICY_ERROR", "Unsupported partition order", "tool_dispatch")


def select(snapshot: Snapshot, request: AnalysisRequest, strategy: Strategy = "indexed") -> Selection:
    if snapshot.dataset_id != request.dataset_id:
        raise HousingError("DATA_INVALID", "Request dataset ID does not match the bound snapshot")
    if not set(request.visible_months).issubset(snapshot.months):
        raise HousingError("DATA_INCOMPLETE", "All twelve visible months must be present")
    available = tuple(m for m in request.required_months if m in snapshot.months)
    missing: tuple[tuple[str, str], ...] = ()
    if strategy == "indexed":
        partitions = tuple((m, z) for m in available for z in request.criteria.zips)
        missing = tuple(key for key in partitions if key not in snapshot.index)
        candidates = tuple(row for key in partitions for row in snapshot.index.get(key, ()))
    elif strategy == "full_csv":
        # Reparse immutable source bytes instead of reading the possibly faulty index.
        candidates = tuple(row for row in parse_csv(snapshot.raw_csv).rows if row.month in available)
    elif strategy == "rebuilt_index":
        rebuilt: dict[tuple[str, str], list[Observation]] = {
            (m, z): [] for m in available for z in request.criteria.zips
        }
        for row in parse_csv(snapshot.raw_csv).rows:
            if (row.month, row.zip) in rebuilt:
                rebuilt[row.month, row.zip].append(row)
        candidates = tuple(row for key in sorted(rebuilt) for row in rebuilt[key])
    else:
        raise HousingError("AGENT_POLICY_ERROR", "Unknown scan strategy", "selection")
    rows = tuple(row for row in candidates if matches(row, request))
    return Selection(
        snapshot,
        request,
        strategy,
        rows,
        available,
        missing,
        semantic_hash(sorted(row.record_id for row in rows)),
        semantic_hash(request.housing_query(snapshot.view_sha256)),
    )
