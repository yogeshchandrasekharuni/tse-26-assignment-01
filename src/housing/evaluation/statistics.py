"""Base-level Wilson intervals computed with decimal square roots, never binary floats."""

from decimal import Decimal, localcontext


def wilson(x: int, n: int) -> tuple[str | None, str | None, str | None]:
    if n < 0 or not 0 <= x <= n:
        raise ValueError("Wilson requires 0 <= x <= n")
    if n == 0:
        return None, None, None
    with localcontext() as context:
        context.prec = 60
        z = Decimal("1.959963984540054")
        nn = Decimal(n)
        p = Decimal(x) / nn
        d = 1 + z * z / nn
        center = (p + z * z / (2 * nn)) / d
        half = z / d * (p * (1 - p) / nn + z * z / (4 * nn * nn)).sqrt()
        low, high = max(Decimal(0), center - half), min(Decimal(1), center + half)
        return format(p, ".24f"), format(low, ".24f"), format(high, ".24f")
