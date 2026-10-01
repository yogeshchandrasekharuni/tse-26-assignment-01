"""No floating-point filtering, statistics or display rounding."""

from collections.abc import Iterable
from fractions import Fraction

SQFT_TO_SQM = Fraction(9290304, 100000000)


def round_half_even(value: Fraction) -> int:
    quotient, remainder = divmod(abs(value.numerator), value.denominator)
    if 2 * remainder > value.denominator or (2 * remainder == value.denominator and quotient % 2):
        quotient += 1
    return -quotient if value < 0 else quotient


def serial(value: Fraction | int | None, digits: int = 6) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (Fraction, int)) or isinstance(value, bool):
        raise TypeError("Exact serialization requires Fraction or int")
    if not 0 <= digits <= 12:
        raise ValueError("Unsupported decimal precision")
    scaled = round_half_even(Fraction(value) * 10**digits)
    sign = "-" if scaled < 0 else ""
    integer, decimal = divmod(abs(scaled), 10**digits)
    return f"{sign}{integer}.{decimal:0{digits}d}" if digits else f"{sign}{integer}"


def median(values: Iterable[Fraction]) -> Fraction | None:
    ordered = sorted(values)
    n = len(ordered)
    return None if not n else ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def percentage(current: Fraction | int | None, previous: Fraction | int | None) -> Fraction | None:
    if current is None or previous is None or previous == 0:
        return None
    return 100 * (Fraction(current) / Fraction(previous) - 1)
