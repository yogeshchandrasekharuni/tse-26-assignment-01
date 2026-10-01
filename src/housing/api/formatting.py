"""Exact display and chart geometry. The browser never recalculates canonical statistics."""

from fractions import Fraction
from typing import Literal, cast

from housing.api.models import AnalysisView, AxisTick, MonthView, PlotPoint
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.tools.aggregate import present
from housing.tools.exact import round_half_even, serial

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def decimal6(value: Fraction) -> str:
    return cast(str, serial(value))


def rounded(value: str | Fraction, places: int = 0) -> str:
    factor = 10**places
    integer = round_half_even(Fraction(value) * factor)
    sign = "−" if integer < 0 else ""
    whole, tail = divmod(abs(integer), factor)
    return sign + f"{whole:,}" + (f".{tail:0{places}d}" if places else "")


def pct(value: str | None) -> str:
    return "Unavailable" if value is None else ("+" if Fraction(value) > 0 else "") + rounded(value, 2) + "%"


def axis(
    values: tuple[str | None, ...], *, prefix: str, places: int, suffix: str = ""
) -> tuple[tuple[AxisTick, ...], tuple[str | None, ...]]:
    known = [Fraction(value) for value in values if value is not None]
    low, high = (min(known), max(known)) if known else (Fraction(0), Fraction(1))
    padding = (high - low) / 6 if high != low else max(high / 10, Fraction(1))
    low, high = max(Fraction(0), low - padding), high + padding
    span = high - low
    ticks = tuple(
        AxisTick(y=decimal6(Fraction(i, 4)), label=prefix + rounded(high - span * i / 4, places) + suffix)
        for i in range(5)
    )
    points = tuple(
        decimal6((high - Fraction(value)) / span) if value is not None else None for value in values
    )
    return ticks, points


def analysis_view(
    output: AnalysisOutput,
    request: AnalysisRequest,
    *,
    reference: str,
    origin: Literal["live_capture", "live", "replay"],
    purpose: Literal["analysis", "development_smoke", "auxiliary_index_omission"] = "analysis",
    money: Literal["USD", "USD_THOUSANDS"] | None = None,
    area: Literal["SQFT", "SQM"] | None = None,
) -> AnalysisView:
    # Display preferences never alter the recorded request, selection or canonical output.
    display = request.display.model_copy(
        update={"money": money or request.display.money, "area": area or request.display.area}
    )
    presentation = present(output.canonical, display)
    price_values = tuple(m.median_price for m in presentation.monthly)
    ppsf_values = tuple(m.median_price_per_area for m in presentation.monthly)
    count_values = tuple(str(m.listing_count) for m in output.canonical.monthly)
    suffix = "k" if display.money == "USD_THOUSANDS" else ""
    price_ticks, price_y = axis(price_values, prefix="$", places=1 if suffix else 0, suffix=suffix)
    ppsf_ticks, ppsf_y = axis(ppsf_values, prefix="$", places=2, suffix=suffix)
    count_ticks, count_y = axis(count_values, prefix="", places=0)
    months = []
    for i, (canonical, shown) in enumerate(zip(output.canonical.monthly, presentation.monthly, strict=True)):
        month_name = MONTHS[int(canonical.month[5:]) - 1]
        x = decimal6(Fraction(i, 11))
        months.append(
            MonthView(
                month=canonical.month,
                label=f"{month_name} {canonical.month[:4]}",
                short_label=month_name[:3],
                observations=f"{canonical.listing_count:,}",
                price="$" + rounded(shown.median_price, 1 if suffix else 0) + suffix
                if shown.median_price is not None
                else "No observations",
                price_per_area="$" + rounded(shown.median_price_per_area, 2) + suffix
                if shown.median_price_per_area is not None
                else "Unavailable",
                price_mom=pct(canonical.price_mom_pct),
                price_yoy=pct(canonical.price_yoy_pct),
                ppsf_mom=pct(canonical.ppsf_mom_pct),
                count_mom=pct(canonical.count_mom_pct),
                price_plot=PlotPoint(x=x, y=price_y[i]),
                ppsf_plot=PlotPoint(x=x, y=ppsf_y[i]),
                count_plot=PlotPoint(x=x, y=count_y[i]),
                support="empty"
                if canonical.listing_count == 0
                else "sparse"
                if canonical.listing_count < 5
                else "supported",
            )
        )
    return AnalysisView(
        output=output,
        request=request,
        origin=origin,
        purpose=purpose,
        months=tuple(months),
        price_ticks=price_ticks,
        ppsf_ticks=ppsf_ticks,
        count_ticks=count_ticks,
        money_unit="USD thousands" if suffix else "USD",
        area_unit="m²" if display.area == "SQM" else "sq ft",
        total_label=f"{output.canonical.summary.total_observations:,}",
        window_change_label=pct(output.canonical.summary.window_price_change_pct),
        last_yoy_label=pct(output.canonical.summary.last_month_price_yoy_pct),
        csv_url=reference + "/export.csv",
        json_url=reference + "/export.json",
        trace_url=reference + "/trace",
    )
