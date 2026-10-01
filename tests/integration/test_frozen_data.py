"""Exercise the committed snapshot through ingestion, selection and all numeric roles."""

import pytest

from housing.contracts.common import ZIPS, PartitionOrder, Strategy
from housing.contracts.decisions import PriceDecision, RegionDecision, SupplyDecision
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH, freeze
from housing.data.store import load_snapshot, select
from housing.tools.statistics import price_stats, region_stats, supply_stats


@pytest.mark.parametrize(
    ("zips", "bedrooms", "minimum", "maximum"),
    [
        (ZIPS, (1, 5), None, None),
        (("75001", "75204"), (2, 4), 20_000_000, 45_000_000),
        (("75006",), (5, 5), 80_000_000, None),
        (("75001",), (1, 1), 1, 1),
    ],
)
def test_index_full_scan_and_rebuild_agree(
    zips: tuple[str, ...], bedrooms: tuple[int, int], minimum: int | None, maximum: int | None
) -> None:
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    request = AnalysisRequest.model_validate(
        {
            "dataset_id": snapshot.dataset_id,
            "window_end": "2026-09",
            "criteria": {
                "zips": zips,
                "property_types": ("single_family", "condo", "townhouse"),
                "bedrooms_min": bedrooms[0],
                "bedrooms_max": bedrooms[1],
                "price_min_cents": minimum,
                "price_max_cents": maximum,
                "sqft_min": None,
                "sqft_max": None,
            },
            "display": {"money": "USD", "area": "SQFT"},
            "compare_regions": True,
            "seed": 104729,
        }
    )
    strategies: tuple[Strategy, ...] = ("indexed", "full_csv", "rebuilt_index")
    selections = [select(snapshot, request, strategy) for strategy in strategies]
    assert len({s.selection_sha256 for s in selections}) == 1
    assert all(s.scan_complete for s in selections)
    prices, supplies, regions = [], [], []
    orders: tuple[PartitionOrder, ...] = ("month_asc", "zip_asc", "month_asc")
    for s, order in zip(selections, orders, strict=True):
        prices.append(
            price_stats(
                s,
                PriceDecision(
                    role="price",
                    decision_type="tool_intent",
                    tool="price_stats",
                    partition_order=order,
                    purpose="statistics",
                ),
            )
        )
        supplies.append(
            supply_stats(
                s,
                SupplyDecision(
                    role="supply",
                    decision_type="tool_intent",
                    tool="supply_stats",
                    partition_order=order,
                    purpose="statistics",
                ),
            )
        )
        regions.append(
            region_stats(
                s,
                RegionDecision(
                    role="region",
                    decision_type="tool_intent",
                    tool="region_stats",
                    partition_order=order,
                    purpose="public_comparison",
                ),
            )
        )
    assert prices[0] == prices[1] == prices[2]
    assert supplies[0] == supplies[1] == supplies[2]
    assert regions[0] == regions[1] == regions[2]


def test_frozen_generation_matches_committed_bytes_and_provenance() -> None:
    before = (CSV_PATH.read_bytes(), MANIFEST_PATH.read_bytes())
    manifest = freeze()  # Two fresh generations, strict ingestion and all provenance comparisons.
    assert manifest.actual_rows == manifest.valid_rows == 34560
    assert manifest.quarantined_rows == 0
    assert before == (CSV_PATH.read_bytes(), MANIFEST_PATH.read_bytes())
