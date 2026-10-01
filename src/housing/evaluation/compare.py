"""Declared MR projections. Rational comparisons never coerce null or use floats."""

import re
from decimal import Decimal, localcontext
from fractions import Fraction

from pydantic import JsonValue

from housing.contracts.output import AnalysisOutput
from housing.evaluation.models import CaseSpec, Comparison, Difference


def decimal_text(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 60
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".24f")


def number(value: JsonValue) -> Fraction | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int) or (
        isinstance(value, str) and re.fullmatch(r"-?(0|[1-9][0-9]*)\.[0-9]+", value)
    ):
        try:
            return Fraction(value)
        except ValueError:
            return None
    return None


class Checks:
    def __init__(self) -> None:
        self.numeric_count = 0
        self.maximum_error = Fraction(0)
        self.differences: list[Difference] = []

    def scalar(
        self,
        path: str,
        source: JsonValue,
        followup: JsonValue,
        *,
        expected: JsonValue | Fraction = None,
        rule: str = "equal",
        tolerance: Fraction = Fraction(0),
        count_numeric: bool = True,
    ) -> None:
        target = source if expected is None else expected
        a = target if isinstance(target, Fraction) else number(target)
        b = number(followup)
        error = abs(b - a) if a is not None and b is not None else None
        if error is not None and count_numeric:
            self.numeric_count += 1
            self.maximum_error = max(self.maximum_error, error)
        if rule == "equal":
            passed = followup == target
        elif rule == "absolute_tolerance":
            passed = (target is None and followup is None) or (error is not None and error <= tolerance)
        elif rule in {"at_least", "at_most"}:
            passed = a is not None and b is not None and (b >= a if rule == "at_least" else b <= a)
        else:
            raise ValueError(f"Unknown comparison rule: {rule}")
        if not passed:
            self.differences.append(
                Difference(
                    path=path,
                    source=source,
                    followup=followup,
                    expected=decimal_text(target) if isinstance(target, Fraction) else target,
                    rule=rule,
                    absolute_error=decimal_text(error) if error is not None else None,
                    tolerance=decimal_text(tolerance) if rule == "absolute_tolerance" else None,
                )
            )

    def exact(self, source: JsonValue, followup: JsonValue, path: str) -> None:
        if isinstance(source, dict) and isinstance(followup, dict):
            if set(source) != set(followup):
                self.scalar(path + ".fields", ",".join(sorted(source)), ",".join(sorted(followup)))
            for key in sorted(source.keys() & followup.keys()):
                self.exact(source[key], followup[key], path + "." + key)
        elif isinstance(source, list) and isinstance(followup, list):
            self.scalar(path + ".length", len(source), len(followup), count_numeric=False)
            for i, (a, b) in enumerate(zip(source, followup)):
                self.exact(a, b, f"{path}[{i}]")
        else:
            self.scalar(path, source, followup)

    def result(self) -> Comparison:
        return Comparison(
            status="violation" if self.differences else "pass",
            compared_numeric_count=self.numeric_count,
            max_absolute_error=decimal_text(self.maximum_error),
            differences=tuple(self.differences),
        )


def compare(case: CaseSpec, source: AnalysisOutput, followup: AnalysisOutput) -> Comparison:
    if not case.eligibility.eligible:
        raise ValueError("Cannot compare an ineligible case")
    checks = Checks()
    a, b = source.canonical.model_dump(mode="json"), followup.canonical.model_dump(mode="json")
    before = {row.month: row for row in source.canonical.monthly}
    after = {row.month: row for row in followup.canonical.monthly}
    mr = case.mr
    if mr in {"MR01", "MR02", "MR04", "MR10"}:
        checks.exact(a, b, "canonical")
    if mr == "MR03":
        checks.scalar(
            "canonical.window_start", source.canonical.window_start, followup.canonical.window_start
        )
        checks.scalar("canonical.window_end", source.canonical.window_end, followup.canonical.window_end)
        for old_row, new_row in zip(source.canonical.monthly, followup.canonical.monthly, strict=True):
            for name, value in old_row.model_dump(mode="json").items():
                checks.scalar(
                    f"canonical.monthly.{old_row.month}.{name}",
                    value,
                    getattr(new_row, name),
                    expected=2 * value if name == "listing_count" else None,
                )
        for name, value in a["summary"].items():
            if name == "total_observations":
                checks.scalar("canonical.summary." + name, value, b["summary"][name], expected=2 * value)
            else:
                checks.exact(value, b["summary"][name], "canonical.summary." + name)
    if mr == "MR04":
        for output in (source, followup):
            scale_money = Fraction(1, 1000) if output.presentation.money == "USD_THOUSANDS" else Fraction(1)
            scale_area = Fraction(100000000, 9290304) if output.presentation.area == "SQM" else Fraction(1)
            for canonical, shown in zip(output.canonical.monthly, output.presentation.monthly, strict=True):
                for name, raw, display, multiplier in (
                    ("median_price", canonical.median_price_usd, shown.median_price, scale_money),
                    (
                        "median_price_per_area",
                        canonical.median_ppsf_usd,
                        shown.median_price_per_area,
                        scale_money * scale_area,
                    ),
                ):
                    expected = Fraction(raw) * multiplier if raw is not None else None
                    checks.scalar(
                        f"presentation.{output.presentation.money}.{canonical.month}.{name}",
                        raw,
                        display,
                        expected=expected,
                        rule="absolute_tolerance",
                        tolerance=Fraction(1, 1000000),
                    )
    if mr in {"MR05", "MR06"}:
        checks.exact(list(before), list(after), "canonical.month_labels")
        strict = False
        for month in sorted(before.keys() & after.keys()):
            old_count, new_count = before[month].listing_count, after[month].listing_count
            checks.scalar(
                f"canonical.monthly.{month}.listing_count",
                old_count,
                new_count,
                rule="at_least" if mr == "MR05" else "at_most",
            )
            strict |= new_count > old_count if mr == "MR05" else new_count < old_count
        checks.scalar("strict_count_witness", "required", "required" if strict else "absent")
        checks.scalar(
            "canonical.summary.total_observations",
            source.canonical.summary.total_observations,
            followup.canonical.summary.total_observations,
            rule="at_least" if mr == "MR05" else "at_most",
        )
        if mr == "MR06" and case.source_request.compare_regions:
            regional = {r.zip: r.median_ppsf_usd for r in source.canonical.summary.zip_rankings}
            for row in followup.canonical.summary.zip_rankings:
                checks.scalar(
                    f"canonical.summary.zip.{row.zip}.median_ppsf_usd",
                    regional.get(row.zip),
                    row.median_ppsf_usd,
                )
    if mr == "MR07":
        overlap = sorted(before.keys() & after.keys())
        checks.scalar("canonical.overlap.length", 11, len(overlap))
        checks.scalar("canonical.window_end", case.followup_request.window_end, followup.canonical.window_end)
        for month in overlap:
            checks.exact(
                before[month].model_dump(mode="json"),
                after[month].model_dump(mode="json"),
                f"canonical.monthly.{month}",
            )
        outgoing, incoming = source.canonical.monthly[0], followup.canonical.monthly[-1]
        total = source.canonical.summary.total_observations - outgoing.listing_count + incoming.listing_count
        checks.scalar(
            "canonical.summary.total_observations", total, followup.canonical.summary.total_observations
        )
    if mr == "MR08":
        k = Fraction(case.recipe.factor_numerator, case.recipe.factor_denominator)
        checks.exact(list(before), list(after), "canonical.month_labels")
        for month in sorted(before.keys() & after.keys()):
            old_fields, new_fields = (
                before[month].model_dump(mode="json"),
                after[month].model_dump(mode="json"),
            )
            for name, value in old_fields.items():
                path = f"canonical.monthly.{month}.{name}"
                if name in {"median_price_usd", "median_ppsf_usd"}:
                    expected = Fraction(value) * k if value is not None else None
                    checks.scalar(
                        path,
                        value,
                        new_fields[name],
                        expected=expected,
                        rule="absolute_tolerance",
                        tolerance=Fraction(3, 1000000),
                    )
                elif name.endswith("_pct") and name != "count_mom_pct":
                    checks.scalar(
                        path,
                        value,
                        new_fields[name],
                        rule="absolute_tolerance",
                        tolerance=Fraction(1, 1000000),
                    )
                else:
                    checks.scalar(path, value, new_fields[name])
        sa, sb = source.canonical.summary, followup.canonical.summary
        checks.scalar("canonical.summary.total_observations", sa.total_observations, sb.total_observations)
        for name in (
            "window_price_change_pct",
            "window_ppsf_change_pct",
            "last_month_price_yoy_pct",
            "last_month_ppsf_yoy_pct",
        ):
            checks.scalar(
                "canonical.summary." + name,
                getattr(sa, name),
                getattr(sb, name),
                rule="absolute_tolerance",
                tolerance=Fraction(1, 1000000),
            )
        checks.scalar("canonical.summary.zip_rankings.length", len(sa.zip_rankings), len(sb.zip_rankings))
        for old_zip, new_zip in zip(sa.zip_rankings, sb.zip_rankings):
            checks.scalar("canonical.summary.zip.label", old_zip.zip, new_zip.zip)
            checks.scalar(f"canonical.summary.zip.{old_zip.zip}.rank", old_zip.rank, new_zip.rank)
            expected = Fraction(old_zip.median_ppsf_usd) * k if old_zip.median_ppsf_usd is not None else None
            checks.scalar(
                f"canonical.summary.zip.{old_zip.zip}.median_ppsf_usd",
                old_zip.median_ppsf_usd,
                new_zip.median_ppsf_usd,
                expected=expected,
                rule="absolute_tolerance",
                tolerance=Fraction(3, 1000000),
            )
    if mr == "MR09":
        checks.exact(list(before), list(after), "canonical.month_labels")
        for month in sorted(before.keys() & after.keys()):
            old, new = before[month], after[month]
            checks.scalar(f"canonical.monthly.{month}.listing_count", old.listing_count, new.listing_count)
            if month == case.recipe.target_month:
                d = Fraction(case.recipe.delta_cents, 100)
                expected = Fraction(old.median_price_usd) + d if old.median_price_usd is not None else None
                checks.scalar(
                    f"canonical.monthly.{month}.median_price_usd",
                    old.median_price_usd,
                    new.median_price_usd,
                    expected=expected,
                    rule="absolute_tolerance",
                    tolerance=Fraction(1, 1000000),
                )
                sqft = case.eligibility.witnesses["max_selected_sqft"]
                if not isinstance(sqft, int) or sqft <= 0 or old.median_ppsf_usd is None:
                    raise ValueError("Invalid additive witness")
                lower = Fraction(old.median_ppsf_usd) + d / sqft - Fraction(3, 1000000)
                checks.scalar(
                    f"canonical.monthly.{month}.median_ppsf_usd",
                    old.median_ppsf_usd,
                    new.median_ppsf_usd,
                    expected=lower,
                    rule="at_least",
                )
            else:
                checks.scalar(
                    f"canonical.monthly.{month}.median_price_usd", old.median_price_usd, new.median_price_usd
                )
                checks.scalar(
                    f"canonical.monthly.{month}.median_ppsf_usd", old.median_ppsf_usd, new.median_ppsf_usd
                )
        checks.scalar(
            "canonical.summary.total_observations",
            source.canonical.summary.total_observations,
            followup.canonical.summary.total_observations,
        )
    result = checks.result()
    if result.compared_numeric_count == 0:
        raise ValueError("Eligible comparison was numerically vacuous")
    return result
