from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from conftest import observation, request, snapshot

from housing.contracts.decisions import PriceDecision, RegionDecision, SupplyDecision
from housing.contracts.errors import HousingError
from housing.contracts.request import Display
from housing.contracts.stats import WorkflowPlan
from housing.data.store import Selection, select
from housing.identity import semantic_hash
from housing.tools.aggregate import aggregate, present
from housing.tools.exact import serial
from housing.tools.statistics import dispatch


def plan_for(selection: Selection) -> WorkflowPlan:
    return WorkflowPlan(
        version=0,
        canonical_query_sha256=selection.query_sha256,
        dataset_view_sha256=selection.snapshot.view_sha256,
        visible_months=selection.request.visible_months,
        required_months=selection.request.required_months,
        scan_strategy=selection.strategy,
        active_specialists=("price", "supply", "region")
        if selection.request.compare_regions
        else ("price", "supply"),
        region_purpose="public_comparison" if selection.request.compare_regions else "none",
        trigger_review_event_sequence=None,
        planner_decision_sha256="a" * 64,
    )


def compute(selection: Selection, directory: Path):
    plan = plan_for(selection)
    decisions: list[PriceDecision | SupplyDecision | RegionDecision] = [
        PriceDecision(
            role="price",
            decision_type="tool_intent",
            tool="price_stats",
            partition_order="month_asc",
            purpose="statistics",
        ),
        SupplyDecision(
            role="supply",
            decision_type="tool_intent",
            tool="supply_stats",
            partition_order="zip_asc",
            purpose="statistics",
        ),
    ]
    executions = [dispatch(selection, plan, d, "unit-run", directory) for d in decisions]
    if selection.request.compare_regions:
        executions.append(
            dispatch(
                selection,
                plan,
                RegionDecision(
                    role="region",
                    decision_type="tool_intent",
                    tool="region_stats",
                    partition_order="zip_asc",
                    purpose="public_comparison",
                ),
                "unit-run",
                directory,
            )
        )
    return aggregate(selection.request, plan, tuple(executions)), tuple(executions)


def test_median_of_individual_ratios_and_observation_count(tmp_path: Path) -> None:
    data = snapshot((observation("a", "2026-09", 10000, 1), observation("b", "2026-09", 20000, 4)))
    canonical, _ = compute(select(data, request()), tmp_path)
    last = canonical.monthly[-1]
    assert last.listing_count == 2
    assert last.median_price_usd == "150.000000"
    assert last.median_ppsf_usd == "75.000000"  # Ratio of medians would be 60.
    assert canonical.monthly[0].median_price_usd is None


def test_lookback_not_first_visible_and_no_intermediate_rounding(tmp_path: Path) -> None:
    data = snapshot(
        tuple(
            observation(f"r{i}", m, p)
            for i, (m, p) in enumerate(
                [("2024-10", 10000), ("2025-09", 20000), ("2025-10", 30000), ("2026-09", 33000)]
            )
        )
    )
    canonical, _ = compute(select(data, request()), tmp_path)
    first = canonical.monthly[0]
    assert first.price_mom_pct == "50.000000" and first.price_yoy_pct == "200.000000"
    assert canonical.summary.window_price_change_pct == "10.000000"
    assert canonical.summary.last_month_price_yoy_pct == "65.000000"
    assert canonical.monthly[1].count_mom_pct == "-100.000000"
    assert canonical.monthly[2].count_mom_pct is None


def test_unavailable_lookback_and_complete_zero_are_distinct(tmp_path: Path) -> None:
    canonical, executions = compute(select(snapshot((), start="2025-10"), request()), tmp_path)
    assert canonical.monthly[0].listing_count == 0
    assert canonical.monthly[0].count_mom_pct is None
    assert canonical.summary.total_observations == 0
    price = executions[0].result
    assert price.monthly[0].count is None and not price.monthly[0].available
    assert price.monthly[12].count == 0 and price.monthly[12].available
    assert len(executions[0].receipt.unavailable_lookback_months) == 12


def test_zip_pooling_exact_ties_no_data_and_display_conversion(tmp_path: Path) -> None:
    rows = (
        observation("a", "2025-10", 10000, zip_code="75001"),
        observation("b", "2025-10", 10000, zip_code="75001"),
        observation("c", "2026-09", 90000, zip_code="75001"),
        observation("d", "2026-09", 10000, zip_code="75006"),
    )
    q = request(compare=True, zips=("75001", "75006", "75019"))
    canonical, _ = compute(select(snapshot(rows, zips=q.criteria.zips), q), tmp_path)
    ranks = canonical.summary.zip_rankings
    assert [(z.zip, z.rank, z.median_ppsf_usd) for z in ranks] == [
        ("75001", 1, "100.000000"),
        ("75006", 2, "100.000000"),
        ("75019", None, None),
    ]
    # Pooled median100 differs from mean(monthly medians100,900)=500.
    shown = present(canonical, Display(money="USD_THOUSANDS", area="SQM"))
    assert shown.monthly[-1].median_price == "0.500000"
    assert shown.monthly[-1].median_price_per_area == serial(Fraction(500) / Fraction("0.09290304") / 1000)


def test_receipts_required_and_wrong_selection_cannot_be_aggregated(tmp_path: Path) -> None:
    selection = select(snapshot((observation("a", "2026-09", 10000),)), request())
    _, executions = compute(selection, tmp_path)
    with pytest.raises(HousingError, match="Missing"):
        aggregate(selection.request, plan_for(selection), executions[:1])
    bad = executions[1].receipt.model_copy(update={"selection_sha256": "b" * 64})
    with pytest.raises(HousingError, match="RECEIPT_MISMATCH"):
        aggregate(
            selection.request,
            plan_for(selection),
            (executions[0], executions[1].model_copy(update={"receipt": bad})),
        )
    assert semantic_hash(executions[0].result) == executions[0].receipt.result_sha256
    wrong = replace(selection, query_sha256="c" * 64)
    with pytest.raises(HousingError, match="immutable selection"):
        dispatch(
            wrong,
            plan_for(selection),
            PriceDecision(
                role="price",
                decision_type="tool_intent",
                tool="price_stats",
                partition_order="month_asc",
                purpose="statistics",
            ),
            "bad-run",
            tmp_path,
        )
