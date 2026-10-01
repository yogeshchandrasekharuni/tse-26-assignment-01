import json

import pytest

from housing.contracts.errors import HousingError
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import ingest


def test_missing_source_partition_is_not_a_successful_zero_month() -> None:
    payload = json.loads(MANIFEST_PATH.read_bytes())
    del payload["month_completeness"]["2026-03"]
    manifest = DatasetManifest.model_validate(payload)
    with pytest.raises(HousingError) as error:
        ingest(CSV_PATH.read_bytes(), manifest)
    assert error.value.code == "DATA_INCOMPLETE"


def test_frozen_bytes_and_schema_are_verified_before_ingestion() -> None:
    manifest = DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
    with pytest.raises(HousingError, match="byte hash"):
        ingest(CSV_PATH.read_bytes() + b"\n", manifest)
    bad_schema = manifest.model_copy(update={"row_schema_sha256": "0" * 64})
    with pytest.raises(HousingError, match="row schema"):
        ingest(CSV_PATH.read_bytes(), bad_schema)
