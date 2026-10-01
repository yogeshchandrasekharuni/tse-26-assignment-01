"""Hand-calculated comparator and interval anchors; auxiliary, never campaign evidence."""

from fractions import Fraction

import pytest

from housing.evaluation.compare import Checks, number
from housing.evaluation.statistics import wilson


def test_wilson_uses_distinct_base_denominator_and_empty_is_undefined() -> None:
    assert wilson(0, 0) == (None, None, None)
    assert wilson(0, 30) == (
        "0.000000000000000000000000",
        "0.000000000000000000000000",
        "0.113513393173968749941089",
    )
    assert wilson(15, 30) == (
        "0.500000000000000000000000",
        "0.331541256405337667360937",
        "0.668458743594662332639063",
    )
    assert wilson(30, 30)[1] == "0.886486606826031250058911"
    assert wilson(0, 90)[2] != wilson(0, 30)[2]
    with pytest.raises(ValueError):
        wilson(31, 30)


def test_null_is_never_zero_and_tolerances_have_exact_boundaries() -> None:
    checks = Checks()
    checks.scalar("null", None, None, rule="absolute_tolerance", tolerance=Fraction(1, 1000000))
    assert checks.numeric_count == 0
    checks.scalar("null-zero", None, "0.000000", rule="absolute_tolerance", tolerance=Fraction(1, 1000000))
    checks.scalar("edge", "1.000000", "1.000003", rule="absolute_tolerance", tolerance=Fraction(3, 1000000))
    checks.scalar(
        "outside", "1.000000", "1.000004", rule="absolute_tolerance", tolerance=Fraction(3, 1000000)
    )
    assert [difference.path for difference in checks.differences] == ["null-zero", "outside"]
    assert checks.numeric_count == 2
    assert number("75001") is None and number("2026-06") is None


def test_count_inequality_is_exact_and_lower_bound_stays_rational() -> None:
    checks = Checks()
    checks.scalar("count", 5, 4, rule="at_least")
    checks.scalar("lower", "1.000000", "1.333333", expected=Fraction(4, 3), rule="at_least")
    assert [difference.path for difference in checks.differences] == ["count", "lower"]
    assert checks.differences[1].absolute_error == "0.000000333333333333333333"
