"""Independent eligibility rejects vacuous transforms; no model outcomes are fabricated."""

import pytest

from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import MRS, Recipe
from housing.evaluation.preflight import check
from housing.evaluation.transforms import transform, updated_criteria
from housing.identity import ROOT


@pytest.fixture(scope="module")
def source_request() -> AnalysisRequest:
    return AnalysisRequest.model_validate_json((ROOT / "configs/example-request.json").read_bytes())


def test_all_relations_have_independent_nonvacuous_witnesses(source_request: AnalysisRequest) -> None:
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    manifest = DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
    request = updated_criteria(source_request, zips=("75001", "75006"))
    request = AnalysisRequest.model_validate({**request.model_dump(), "window_end": "2026-08"})
    for mr in MRS:
        source = (
            updated_criteria(request, price_min_cents=20000000, price_max_cents=45000000)
            if mr == "MR05"
            else request
        )
        recipe = Recipe(
            version="transform-1",
            mr=mr,
            transform_seed=12345,
            target_month=source.visible_months[0] if mr == "MR09" else None,
            excluded_zip="75019" if mr == "MR10" else None,
        )
        changed, followup = transform(snapshot, source, recipe, manifest)
        witness = check(snapshot.raw_csv, changed.raw_csv, source, followup, recipe)
        assert witness.eligible, (mr, witness.reasons)
        if mr in {"MR01", "MR02", "MR03", "MR08", "MR09", "MR10"}:
            vacuous = check(snapshot.raw_csv, snapshot.raw_csv, source, followup, recipe)
            assert not vacuous.eligible, mr


def test_preflight_does_not_import_production_selector_or_statistics() -> None:
    # A small architectural guard protects the independent witness oracle from accidental coupling.
    source = (ROOT / "src/housing/evaluation/preflight.py").read_text()
    assert "from housing.data.store" not in source
    assert "from housing.tools" not in source
    assert "from housing.evaluation.compare" not in source
