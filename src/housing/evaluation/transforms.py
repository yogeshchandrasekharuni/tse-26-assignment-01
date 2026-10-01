"""Raw-observation transformations; every follow-up still enters normal ingestion."""

import random
from collections import Counter
from fractions import Fraction

from housing.contracts.request import AnalysisRequest, Criteria, Display
from housing.data.generate import encode_csv
from housing.data.models import DatasetManifest, Observation
from housing.data.store import Snapshot, ingest, logical_hash
from housing.evaluation.models import Recipe
from housing.identity import semantic_hash, sha256_bytes
from housing.tools.calendar import add_month


def updated_request(request: AnalysisRequest, **changes: object) -> AnalysisRequest:
    return AnalysisRequest.model_validate({**request.model_dump(), **changes})


def updated_criteria(request: AnalysisRequest, **changes: object) -> AnalysisRequest:
    criteria = Criteria.model_validate({**request.criteria.model_dump(), **changes})
    return updated_request(request, criteria=criteria)


def relabeled(prefix: str, old: str, seed: int) -> str:
    return prefix + semantic_hash([seed, old])[:32]


def transform(
    snapshot: Snapshot, request: AnalysisRequest, recipe: Recipe, manifest: DatasetManifest
) -> tuple[Snapshot, AnalysisRequest]:
    rows = list(snapshot.rows)
    followup = request
    match recipe.mr:
        case "MR01":
            # Explicit Fisher–Yates, including all raw rows and retaining resulting raw order.
            rng = random.Random(recipe.transform_seed)
            for i in range(len(rows) - 1, 0, -1):
                j = rng.randrange(i + 1)
                rows[i], rows[j] = rows[j], rows[i]
        case "MR02":
            rows = [
                row.model_copy(
                    update={
                        "record_id": relabeled("r-", row.record_id, recipe.transform_seed),
                        "listing_id": relabeled("l-", row.listing_id, recipe.transform_seed),
                    }
                )
                for row in rows
            ]
        case "MR03":
            replicas = [row.model_copy(update={"record_id": "replica-" + row.record_id}) for row in rows]
            if {row.record_id for row in rows} & {row.record_id for row in replicas}:
                raise ValueError("Replication namespace collides")
            rows.extend(replicas)
        case "MR04":
            followup = updated_request(request, display=Display(money="USD_THOUSANDS", area="SQM"))
        case "MR05":
            a, b = request.criteria.price_min_cents, request.criteria.price_max_cents
            if a is None or b is None or a <= 0:
                raise ValueError("MR05 requires a positive finite source band")
            followup = updated_criteria(
                request, price_min_cents=max(0, a - 10000000), price_max_cents=b + 30000000
            )
        case "MR06":
            zips = request.criteria.zips
            followup = updated_criteria(request, zips=zips[: max(1, len(zips) // 2)])
        case "MR07":
            followup = updated_request(request, window_end=add_month(request.window_end, 1))
        case "MR08":
            k = Fraction(recipe.factor_numerator, recipe.factor_denominator)
            if not 1 < k <= 2:
                raise ValueError("Unsupported scale factor")

            def scale(value: int | None) -> int | None:
                if value is None:
                    return None
                product = value * k
                if product.denominator != 1:
                    raise ValueError("Scaling must preserve integer cents")
                return product.numerator

            rows = [row.model_copy(update={"price_cents": scale(row.price_cents)}) for row in rows]
            followup = updated_criteria(
                request,
                price_min_cents=scale(request.criteria.price_min_cents),
                price_max_cents=scale(request.criteria.price_max_cents),
            )
        case "MR09":
            if (
                recipe.target_month is None
                or request.criteria.price_min_cents is not None
                or request.criteria.price_max_cents is not None
            ):
                raise ValueError("MR09 needs a nonempty target month and unbounded price criteria")
            rows = [
                row.model_copy(update={"price_cents": row.price_cents + recipe.delta_cents})
                if row.month == recipe.target_month
                else row
                for row in rows
            ]
        case "MR10":
            if recipe.excluded_zip is None or recipe.excluded_zip in request.criteria.zips:
                raise ValueError("MR10 needs an allowed excluded ZIP")
            c = request.criteria
            sqft = c.sqft_min or 1800
            price = c.price_min_cents or min(c.price_max_cents or 35000000, 35000000)
            for month in snapshot.months:
                # The other fields deliberately satisfy the query: only ZIP excludes these rows.
                rows.append(
                    Observation.model_validate(
                        {
                            "record_id": f"outside-{recipe.transform_seed}-{month}",
                            "listing_id": f"outside-listing-{recipe.transform_seed}-{month}",
                            "month": month,
                            "zip": recipe.excluded_zip,
                            "property_type": c.property_types[0],
                            "bedrooms": c.bedrooms_min,
                            "sqft": sqft,
                            "price_cents": max(1, price),
                        }
                    )
                )
    if recipe.mr in {"MR04", "MR05", "MR06", "MR07"}:
        return snapshot, followup
    materialized = tuple(rows)
    data = encode_csv(materialized)
    counts = Counter(row.month for row in materialized)
    derived = manifest.model_copy(
        update={
            "source_kind": "transformed",
            "generator": None,
            "snapshot_path": f"recipe:{semantic_hash(recipe)}",
            "snapshot_sha256": sha256_bytes(data),
            "logical_multiset_sha256": logical_hash(materialized),
            "expected_rows": len(rows),
            "actual_rows": len(rows),
            "valid_rows": len(rows),
            "partition_row_counts": {m: counts[m] for m in snapshot.months},
        }
    )
    # Validate copied contracts before trusting them; strict ingestion checks every transformed row.
    derived = DatasetManifest.model_validate_json(derived.model_dump_json())
    return ingest(data, derived, source_sha256=snapshot.source_sha256), followup
