"""Independent raw-CSV selector used only for eligibility, never expected statistics.

This module intentionally imports no production selection, median, delta or comparator.
Input witnesses are fixed before the model campaign observes any result.
"""

import csv
import io
from collections import Counter
from dataclasses import dataclass, replace

from housing.contracts.request import AnalysisRequest
from housing.evaluation.models import Eligibility, Recipe
from housing.identity import canonical_json, semantic_hash


@dataclass(frozen=True)
class RawRow:
    record_id: str
    listing_id: str
    month: str
    zip: str
    property_type: str
    bedrooms: int
    sqft: int
    price_cents: int


def raw_rows(data: bytes) -> tuple[RawRow, ...]:
    result = tuple(
        RawRow(
            r["record_id"],
            r["listing_id"],
            r["month"],
            r["zip"],
            r["property_type"],
            int(r["bedrooms"]),
            int(r["sqft"]),
            int(r["price_cents"]),
        )
        for r in csv.DictReader(io.StringIO(data.decode("utf-8")))
    )
    if len({r.record_id for r in result}) != len(result):
        raise ValueError("Independent preflight found duplicate record identity")
    if any(r.price_cents <= 0 or r.sqft <= 0 or not 1 <= r.bedrooms <= 5 for r in result):
        raise ValueError("Independent preflight found invalid arithmetic support")
    return result


def eligible_rows(
    rows: tuple[RawRow, ...], request: AnalysisRequest, *, visible: bool = True
) -> tuple[RawRow, ...]:
    c = request.criteria
    start = request.visible_months[0] if visible else request.required_months[0]
    return tuple(
        r
        for r in rows
        if start <= r.month <= request.window_end
        and r.zip in c.zips
        and r.property_type in c.property_types
        and c.bedrooms_min <= r.bedrooms <= c.bedrooms_max
        and (c.sqft_min is None or c.sqft_min <= r.sqft)
        and (c.sqft_max is None or r.sqft <= c.sqft_max)
        and (c.price_min_cents is None or c.price_min_cents <= r.price_cents)
        and (c.price_max_cents is None or r.price_cents <= c.price_max_cents)
    )


def check(
    source: bytes, followup: bytes, request: AnalysisRequest, changed: AnalysisRequest, recipe: Recipe
) -> Eligibility:
    before, after = raw_rows(source), raw_rows(followup)
    selected, selected_after = eligible_rows(before, request), eligible_rows(after, changed)
    ids, ids_after = {r.record_id for r in selected}, {r.record_id for r in selected_after}
    counts = Counter(r.month for r in selected)
    counts_after = Counter(r.month for r in selected_after)
    reasons: list[str] = []
    witness: dict[str, object] = {
        "source_selected": len(selected),
        "followup_selected": len(selected_after),
        "source_membership_sha256": semantic_hash(sorted(ids)),
        "followup_membership_sha256": semantic_hash(sorted(ids_after)),
        "source_month_counts": {m: counts[m] for m in request.visible_months},
        "followup_month_counts": {m: counts_after[m] for m in changed.visible_months},
        "source_witness_ids": sorted(ids)[:4],
        "odd_months": [m for m in request.visible_months if counts[m] % 2 == 1],
        "even_nonempty_months": [m for m in request.visible_months if counts[m] > 0 and counts[m] % 2 == 0],
        "sparse_months": [m for m in request.visible_months if counts[m] < 5],
    }

    def require(condition: bool, reason: str) -> None:
        if not condition:
            reasons.append(reason)

    require(bool(selected) and bool(selected_after), "Both visible selections must be nonempty")
    require(set(request.visible_months) <= {r.month for r in before}, "Source visible partitions incomplete")
    require(
        set(changed.visible_months) <= {r.month for r in after}, "Follow-up visible partitions incomplete"
    )
    match recipe.mr:
        case "MR01":
            require(len(selected) >= 2, "Permutation needs two selected observations")
            require(source != followup and before != after, "Permutation must change raw bytes/order")
            require(Counter(before) == Counter(after), "Permutation must retain the complete multiset")
        case "MR02":
            require(len({r.record_id for r in before}) >= 2, "Relabel needs distinct IDs")
            require(not ids & ids_after, "Selected record identities must change")
            old_listing = Counter(r.listing_id for r in before)
            new_listing = Counter(r.listing_id for r in after)
            require(
                sorted(old_listing.values()) == sorted(new_listing.values()),
                "Listing equality partition must persist",
            )
            # Check one-to-one correspondence positionally, independent of transform's hashing function.
            record_map = {a.record_id: b.record_id for a, b in zip(before, after, strict=True)}
            listing_map = {a.listing_id: b.listing_id for a, b in zip(before, after, strict=True)}
            require(len(set(record_map.values())) == len(record_map), "Record mapping must be bijective")
            require(len(set(listing_map.values())) == len(listing_map), "Listing mapping must be bijective")
            require(
                all(listing_map[a.listing_id] == b.listing_id for a, b in zip(before, after, strict=True)),
                "Repeated listing labels must map consistently",
            )
            require(
                {record_map[i] for i in ids} == ids_after, "Relabel must preserve selected correspondence"
            )
            require(
                all(
                    replace(a, record_id=b.record_id, listing_id=b.listing_id) == b
                    for a, b in zip(before, after, strict=True)
                ),
                "Relabel must leave every semantic field unchanged",
            )
        case "MR03":
            raw_after = {row.record_id: row for row in after}
            require(
                all(
                    raw_after.get(row.record_id) == row
                    and raw_after.get("replica-" + row.record_id)
                    == replace(row, record_id="replica-" + row.record_id)
                    for row in before
                ),
                "Replication must retain and clone every complete raw observation",
            )
            require(len(after) == 2 * len(before), "Replication must double raw observations")
            require(
                ids_after == ids | {"replica-" + i for i in ids},
                "Every selected observation needs exactly one clone",
            )
            require(
                all(counts_after[m] == 2 * counts[m] for m in request.visible_months),
                "Replication membership must double by month",
            )
        case "MR04":
            require(source == followup and ids == ids_after, "Display cannot mutate input membership")
            require(request.display != changed.display, "Display units must change")
        case "MR05":
            added = ids_after - ids
            require(ids <= ids_after and bool(added), "Widening needs strict membership inclusion")
            witness["added_ids"] = sorted(added)[:4]
            witness["added_count"] = len(added)
        case "MR06":
            removed = ids - ids_after
            require(
                set(changed.criteria.zips) < set(request.criteria.zips),
                "ZIP set must be a nonempty strict subset",
            )
            require(ids_after <= ids and bool(removed), "Restriction needs removed and retained witnesses")
            witness["removed_ids"] = sorted(removed)[:4]
            witness["removed_count"] = len(removed)
        case "MR07":
            overlap = sorted(set(request.visible_months) & set(changed.visible_months))
            require(len(overlap) == 11, "Window advance needs exactly eleven shared calendar months")
            require(any(counts[m] for m in overlap), "Window overlap must be nonempty")
            witness["overlap_months"] = overlap
        case "MR08":
            require(ids == ids_after, "Scaled bounds must preserve membership")
            require(
                {r.record_id for r in eligible_rows(before, request, visible=False)}
                == {r.record_id for r in eligible_rows(after, changed, visible=False)},
                "Scaled bounds must also preserve all comparison-period membership",
            )
            require(
                any(
                    counts[a] and counts[b]
                    for a, b in zip(request.visible_months, request.visible_months[1:])
                ),
                "Scaling needs a defined percentage",
            )
            require(
                all(
                    b.price_cents * recipe.factor_denominator == a.price_cents * recipe.factor_numerator
                    for a, b in zip(before, after, strict=True)
                ),
                "Every snapshot price must scale exactly",
            )
        case "MR09":
            require(
                request.criteria.price_min_cents is None and request.criteria.price_max_cents is None,
                "Additive MR requires unbounded price",
            )
            require(ids == ids_after, "Additive mutation must preserve membership")
            target = tuple(r for r in selected if r.month == recipe.target_month)
            require(bool(target), "Target month needs a selected observation")
            require(
                all(
                    b.price_cents
                    == a.price_cents + (recipe.delta_cents if a.month == recipe.target_month else 0)
                    for a, b in zip(before, after, strict=True)
                ),
                "Only the declared month may change",
            )
            witness["target_month"] = recipe.target_month
            witness["max_selected_sqft"] = max((r.sqft for r in target), default=0)
        case "MR10":
            original_ids = {r.record_id for r in before}
            appended = tuple(r for r in after if r.record_id not in original_ids)
            require(
                len(appended) >= 24 and len({r.month for r in appended}) == 24,
                "Append needs one valid row per snapshot month",
            )
            require(
                all(r.zip not in request.criteria.zips for r in appended),
                "Appended rows must be geographically excluded",
            )
            require(ids == ids_after, "Excluded rows must leave selected membership unchanged")
            require(
                any(r.month in request.visible_months for r in appended),
                "Append needs a visible excluded witness",
            )
            witness["excluded_zip"] = recipe.excluded_zip
            witness["appended_count"] = len(appended)
    # Round-trip JSON prevents accidental mutable/custom values in the public witness contract.
    return Eligibility.model_validate_json(
        canonical_json({"eligible": not reasons, "reasons": reasons, "witnesses": witness})
    )
