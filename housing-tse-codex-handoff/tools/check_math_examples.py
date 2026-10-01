#!/usr/bin/env python3
"""Handoff arithmetic QA only. Does not implement or evaluate the housing app."""
from pathlib import Path
from fractions import Fraction
import json
import math
ROOT = Path(__file__).resolve().parents[1]

def serial(value, digits=6):
    if value is None:
        return None
    value = Fraction(value)
    neg = value < 0
    a = abs(value) * (10 ** digits)
    q, rem = divmod(a.numerator, a.denominator)
    if 2 * rem > a.denominator or (2 * rem == a.denominator and q % 2):
        q += 1
    sign = '-' if neg and q else ''
    return f'{sign}{q // (10 ** digits)}.{q % (10 ** digits):0{digits}d}'

def median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

def wilson(x, n):
    if n == 0:
        return None
    assert 0 <= x <= n
    z = 1.959963984540054
    p = x / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z / den * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return max(0, center-half), min(1, center+half)

def main():
    cases = json.loads((ROOT / 'fixtures/metric_cases.json').read_text())
    for c in cases['cases']:
        prices = [Fraction(x, 100) for x in c['prices_cents']]
        ratios = [p / s for p, s in zip(prices, c['sqft'])]
        assert serial(median(prices)) == c['expected_median_price_usd'], c['id']
        assert serial(median(ratios)) == c['expected_median_ppsf_usd'], c['id']
    for c in cases['rounding']:
        assert serial(Fraction(c['rational'])) == c['expected_6dp']
    for c in cases['count_changes']:
        v = Fraction(100) * (Fraction(c['current'], c['previous']) - 1) if c['previous'] else None
        assert serial(v) == c['expected']
    for c in cases['ci_anchors']:
        lo, hi = wilson(c['x'], c['n'])
        assert abs(lo-c['expected_low']) < 1e-12
        assert abs(hi-c['expected_high']) < 1e-12
    assert wilson(0, 0) is None
    # Simple algebra probes for the nontrivial catalog statements.
    prices = [Fraction(100), Fraction(200), Fraction(900)]
    sqft = [1, 4, 5]
    ratios = [p/s for p, s in zip(prices, sqft)]
    k = Fraction(5, 4)
    assert median([k*r for r in ratios]) == k*median(ratios)
    assert median(ratios*2) == median(ratios)
    delta = Fraction(1000)
    new = [(p+delta)/s for p, s in zip(prices, sqft)]
    assert median(new) >= median(ratios) + delta/max(sqft)
    # The tempting median-ppsf additive equality is generally false.
    assert median(new) != median(ratios) + delta/median([Fraction(s) for s in sqft])
    print('PASS: hand-calculated medians, ratio semantics, half-even serialization, null/count rules, scaling/replication/additive algebra and Wilson anchors. No application evaluated.')

if __name__ == '__main__':
    main()
