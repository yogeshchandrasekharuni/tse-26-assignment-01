"""Merge bound specialist receipts; presentation is downstream of canonical serialization."""

from fractions import Fraction

from housing.contracts.errors import HousingError
from housing.contracts.output import Canonical, Monthly, Presentation, PresentedMonth, Summary, ZipRanking
from housing.contracts.request import AnalysisRequest, Display
from housing.contracts.stats import (
    PriceResult,
    Rational,
    RegionResult,
    SupplyResult,
    ToolExecution,
    WorkflowPlan,
)
from housing.identity import semantic_hash
from housing.tools.calendar import add_month
from housing.tools.exact import SQFT_TO_SQM, percentage, serial


def value(rational: Rational | None) -> Fraction | None:
    return rational.fraction() if rational is not None else None


def aggregate(
    request: AnalysisRequest, plan: WorkflowPlan, executions: tuple[ToolExecution, ...]
) -> Canonical:
    if semantic_hash(request.housing_query(plan.dataset_view_sha256)) != plan.canonical_query_sha256:
        raise HousingError("TOOL_ERROR", "Request differs from the bound plan query", "aggregation")
    by_tool = {e.receipt.tool: e for e in executions}
    expected = {f"{role}_stats" for role in plan.active_specialists}
    if len(by_tool) != len(executions) or set(by_tool) != expected:
        raise HousingError("TOOL_ERROR", "Missing, duplicate or extra specialist receipt", "aggregation")
    bindings = set()
    for execution in executions:
        receipt = execution.receipt
        if receipt.result_sha256 != semantic_hash(execution.result):
            raise HousingError("TOOL_ERROR", "Receipt result integrity mismatch", "aggregation")
        if (
            receipt.plan_sha256 != plan.semantic_sha256
            or receipt.canonical_query_sha256 != plan.canonical_query_sha256
            or receipt.dataset_view_sha256 != plan.dataset_view_sha256
            or receipt.strategy != plan.scan_strategy
            or receipt.iteration != plan.version
            or receipt.visible_months != request.visible_months
            or not receipt.source_snapshot_complete
        ):
            raise HousingError("TOOL_ERROR", "Receipt binding differs from this plan", "aggregation")
        bindings.add(
            (
                receipt.run_id,
                receipt.selection_sha256,
                receipt.scan_complete,
                receipt.unavailable_lookback_months,
            )
        )
    if len(bindings) != 1:
        raise HousingError("TOOL_ERROR", "RECEIPT_MISMATCH: selections or coverage differ", "aggregation")
    price = by_tool["price_stats"].result
    supply = by_tool["supply_stats"].result
    if not isinstance(price, PriceResult) or not isinstance(supply, SupplyResult):
        raise HousingError("TOOL_ERROR", "Wrong specialist result types", "aggregation")
    expected_months = request.required_months
    if (
        tuple(m.month for m in price.monthly) != expected_months
        or tuple(m.month for m in supply.monthly) != expected_months
        or [(m.count, m.available) for m in price.monthly] != [(m.count, m.available) for m in supply.monthly]
    ):
        raise HousingError("TOOL_ERROR", "RECEIPT_MISMATCH: month coverage or counts differ", "aggregation")
    prices = {m.month: m for m in price.monthly}
    counts = {m.month: m for m in supply.monthly}
    monthly: list[Monthly] = []
    for month in request.visible_months:
        p, prior, year = (prices[m] for m in (month, add_month(month, -1), add_month(month, -12)))
        count = counts[month].count
        if count is None:
            raise HousingError("DATA_INCOMPLETE", "Visible month is unavailable", "aggregation")
        monthly.append(
            Monthly(
                month=month,
                listing_count=count,
                median_price_usd=serial(value(p.median_price_usd)),
                median_ppsf_usd=serial(value(p.median_ppsf_usd)),
                price_mom_pct=serial(percentage(value(p.median_price_usd), value(prior.median_price_usd))),
                ppsf_mom_pct=serial(percentage(value(p.median_ppsf_usd), value(prior.median_ppsf_usd))),
                price_yoy_pct=serial(percentage(value(p.median_price_usd), value(year.median_price_usd))),
                ppsf_yoy_pct=serial(percentage(value(p.median_ppsf_usd), value(year.median_ppsf_usd))),
                count_mom_pct=serial(percentage(count, counts[add_month(month, -1)].count)),
            )
        )
    rankings: list[ZipRanking] = []
    if "region_stats" in by_tool:
        region = by_tool["region_stats"].result
        if (
            not isinstance(region, RegionResult)
            or region.purpose != plan.region_purpose
            or region.counts != supply.monthly
            or tuple(z.zip for z in region.pooled) != request.criteria.zips
        ):
            raise HousingError("TOOL_ERROR", "RECEIPT_MISMATCH: Region coverage differs", "aggregation")
        if request.compare_regions:
            ordered = sorted(
                region.pooled,
                key=lambda z: (
                    z.median_ppsf_usd is None,
                    -z.median_ppsf_usd.fraction() if z.median_ppsf_usd else Fraction(0),
                    z.zip,
                ),
            )
            for index, z in enumerate(ordered):
                rankings.append(
                    ZipRanking(
                        zip=z.zip,
                        median_ppsf_usd=serial(value(z.median_ppsf_usd)),
                        rank=index + 1 if z.median_ppsf_usd else None,
                    )
                )
    elif request.compare_regions:
        raise HousingError("TOOL_ERROR", "Public comparison requires a Region receipt", "aggregation")
    first, last = prices[request.visible_months[0]], prices[request.visible_months[-1]]
    return Canonical(
        window_start=request.visible_months[0],
        window_end=request.window_end,
        monthly=tuple(monthly),
        summary=Summary(
            window_price_change_pct=serial(
                percentage(value(last.median_price_usd), value(first.median_price_usd))
            ),
            window_ppsf_change_pct=serial(
                percentage(value(last.median_ppsf_usd), value(first.median_ppsf_usd))
            ),
            last_month_price_yoy_pct=monthly[-1].price_yoy_pct,
            last_month_ppsf_yoy_pct=monthly[-1].ppsf_yoy_pct,
            total_observations=sum(m.listing_count for m in monthly),
            zip_rankings=tuple(rankings),
        ),
    )


def present(canonical: Canonical, display: Display) -> Presentation:
    money = 1000 if display.money == "USD_THOUSANDS" else 1
    area = SQFT_TO_SQM if display.area == "SQM" else Fraction(1)
    return Presentation(
        money=display.money,
        area=display.area,
        monthly=tuple(
            PresentedMonth(
                month=m.month,
                median_price=serial(Fraction(m.median_price_usd) / money)
                if m.median_price_usd is not None
                else None,
                median_price_per_area=serial(Fraction(m.median_ppsf_usd) / money / area)
                if m.median_ppsf_usd is not None
                else None,
            )
            for m in canonical.monthly
        ),
    )
