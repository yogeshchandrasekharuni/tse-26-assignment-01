from housing.api.formatting import axis, pct, rounded


def test_display_rounding_is_half_even_and_nulls_stay_explicit() -> None:
    assert rounded("357060.500000") == "357,060"
    assert rounded("357061.500000") == "357,062"
    assert rounded("1.245000", 2) == "1.24"
    assert rounded("1.255000", 2) == "1.26"
    assert rounded("-0.000001", 2) == "0.00"
    assert pct(None) == "Unavailable"
    assert pct("-1.125505") == "−1.13%"


def test_missing_price_levels_do_not_invent_a_dollar_axis() -> None:
    ticks, points = axis((None,) * 12, prefix="$", places=0)
    assert ticks == ()
    assert points == (None,) * 12
