"""Freeze independently eligible cases before observing paired model outcomes."""

import json
from datetime import UTC, datetime
from pathlib import Path

from housing.contracts.common import ZIPS
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import MRS, SEEDS, CaseSpec, Cohort, MRId, Recipe
from housing.evaluation.preflight import check, eligible_rows, raw_rows
from housing.evaluation.transforms import transform, updated_criteria
from housing.identity import ROOT, canonical_json, semantic_hash, sha256_bytes, write_json

CANDIDATES = ROOT / "housing-tse-codex-handoff/templates/base_candidates.json"
CATALOG = ROOT / "housing-tse-codex-handoff/MR_CATALOG.md"


def evaluation_inputs() -> dict[str, str]:
    paths = sorted((ROOT / "src/housing/evaluation").glob("*.py"))
    paths += [
        CANDIDATES,
        CATALOG,
        ROOT / "housing-tse-codex-handoff/EVALUATION_PROTOCOL.md",
        ROOT / "EVALUATION_NOTES.md",
        ROOT / "configs/evaluation-seeds-v1.json",
    ]
    return {str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in paths}


def transform_seed(mr: MRId, base_id: str) -> int:
    # Exact seed recipe supplied with the handoff; separate from dataset and model seeds.
    return int(sha256_bytes(f"housing-mr-v1|{mr}|{base_id}|20261018".encode())[:8], 16)


def build_cohort(destination: Path, *, pilot: bool = False) -> Cohort:
    if destination.exists():
        raise ValueError("Frozen cohorts cannot be overwritten")
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    manifest = DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
    candidates = json.loads(CANDIDATES.read_bytes())["candidates"]
    cases: list[CaseSpec] = []
    rejected: list[CaseSpec] = []
    raw_source = raw_rows(snapshot.raw_csv)
    relations = ("MR01",) if pilot else MRS
    for mr in relations:
        for candidate in candidates:
            base_id = candidate["base_id"]
            if pilot and base_id not in {"b001", "b002", "b010"}:
                continue
            request = AnalysisRequest.model_validate_json(canonical_json(candidate["request"]))
            # Predeclared sparse-coverage revision: g10 retains its existing ZIP/type/bedroom
            # definitions but intersects a narrow raw size band, before any model execution.
            if candidate["slice_group"] == "g10":
                request = updated_criteria(request, sqft_min=2100, sqft_max=2110)
            if mr == "MR05" or (mr == "MR08" and int(base_id[1:]) <= 10):
                request = updated_criteria(request, price_min_cents=20000000, price_max_cents=45000000)
            if mr == "MR09":
                request = updated_criteria(request, price_min_cents=None, price_max_cents=None)
            selected = eligible_rows(raw_source, request)
            target = next((m for m in request.visible_months if any(r.month == m for r in selected)), None)
            recipe = Recipe(
                version="transform-1",
                mr=mr,
                transform_seed=transform_seed(mr, base_id),
                target_month=target if mr == "MR09" else None,
                excluded_zip=next((z for z in ZIPS if z not in request.criteria.zips), None)
                if mr == "MR10"
                else None,
            )
            transformed, followup = transform(snapshot, request, recipe, manifest)
            repeated, repeated_request = transform(snapshot, request, recipe, manifest)
            if transformed.raw_csv != repeated.raw_csv or followup != repeated_request:
                raise ValueError(f"Nondeterministic transform {mr}/{base_id}")
            eligibility = check(snapshot.raw_csv, transformed.raw_csv, request, followup, recipe)
            spec = CaseSpec(
                mr=mr,
                base_id=base_id,
                slice_group=candidate["slice_group"],
                base_query_sha256=semantic_hash(request.housing_query(snapshot.source_sha256)),
                source_request=request,
                followup_request=followup,
                source_view_sha256=snapshot.view_sha256,
                followup_view_sha256=transformed.view_sha256,
                recipe=recipe,
                eligibility=eligibility,
            )
            (cases if eligibility.eligible else rejected).append(spec)
            print(
                f"preflight {mr}/{base_id}: {'eligible' if eligibility.eligible else eligibility.reasons}",
                flush=True,
            )
    expected = 3 if pilot else 30
    for mr in relations:
        group = [case for case in cases if case.mr == mr]
        if len(group) != expected or len({case.base_query_sha256 for case in group}) != expected:
            # Preserve failed candidates before rejecting the cohort. Never replenish after model results.
            write_json(destination.with_suffix(".rejected.json"), {"eligible": cases, "invalid": rejected})
            raise ValueError(f"{mr} lacks {expected} distinct eligible bases")
    counts = [n for case in cases for n in case.eligibility.witnesses["source_month_counts"].values()]  # type: ignore[union-attr]
    if not any(isinstance(n, int) and 0 < n < 5 for n in counts):
        raise ValueError("Cohort lacks sparse nonempty coverage")
    if not any(isinstance(n, int) and n >= 5 for n in counts):
        raise ValueError("Cohort lacks dense coverage")
    if not any(isinstance(n, int) and n % 2 == 1 for n in counts):
        raise ValueError("Cohort lacks odd median cardinality")
    if not any(isinstance(n, int) and n > 0 and n % 2 == 0 for n in counts):
        raise ValueError("Cohort lacks even median cardinality")
    cohort = Cohort.model_validate_json(
        canonical_json(
            {
                "version": "cohort-1",
                "frozen_at_utc": datetime.now(UTC).isoformat(),
                "candidate_recipe": "handoff thirty slices; coverage revision 2: g10 sqft in [2100,2110] for all three end months; MR-specific price bands applied before base identity; no outcome-based selection",
                "source_snapshot_sha256": snapshot.source_sha256,
                "evaluation_inputs": evaluation_inputs(),
                "seeds": SEEDS,
                "cases": cases,
                "invalid_candidates": rejected,
                "coverage": {
                    "eligible_by_mr": {mr: sum(c.mr == mr for c in cases) for mr in relations},
                    "end_months": sorted({c.source_request.window_end for c in cases}),
                    "slice_groups": sorted({c.slice_group for c in cases}),
                    "visible_month_cells": len(counts),
                    "empty_cells": sum(n == 0 for n in counts),
                    "sparse_nonempty_cells": sum(isinstance(n, int) and 0 < n < 5 for n in counts),
                    "dense_cells": sum(isinstance(n, int) and n >= 5 for n in counts),
                    "odd_cells": sum(isinstance(n, int) and n % 2 == 1 for n in counts),
                    "even_nonempty_cells": sum(isinstance(n, int) and n > 0 and n % 2 == 0 for n in counts),
                    "interpretation": "Overlapping designed convenience queries on one synthetic feed; not a probability sample",
                },
            }
        )
    )
    write_json(destination, cohort)
    return cohort
