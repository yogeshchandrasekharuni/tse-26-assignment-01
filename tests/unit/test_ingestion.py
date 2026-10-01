from dataclasses import replace

import pytest
from conftest import csv_bytes, observation, request, snapshot

from housing.contracts.errors import HousingError
from housing.data.store import logical_hash, parse_csv, select


def test_equal_listing_ids_count_but_duplicate_record_id_aborts() -> None:
    rows = (observation("first", "2026-09", 10000), observation("second", "2026-09", 20000))
    parsed = parse_csv(csv_bytes(rows))
    assert len(parsed.rows) == 2
    with pytest.raises(HousingError, match="Duplicate record_id"):
        parse_csv(csv_bytes((rows[0], rows[0])))


def test_bad_rows_are_quarantined_without_price_repair() -> None:
    data = csv_bytes((observation("ok", "2026-09", 10000),))
    data += b"bad,listing,2026-09,75001,condo,2,1000,-1\n"
    data += b"bad-month,listing,2026-13,75001,condo,2,1000,10000\n"
    parsed = parse_csv(data)
    assert parsed.raw_count == 3 and len(parsed.rows) == 1 and len(parsed.quarantine) == 2
    assert parsed.month_counts == {"2026-09": 2}
    assert parsed.unbucketed_count == 1
    assert "price_cents" in parsed.quarantine[0].reason


def test_header_bom_and_noninteger_numeric_text_are_rejected() -> None:
    data = csv_bytes((observation("one", "2026-09", 10000),))
    with pytest.raises(HousingError, match="header"):
        parse_csv(data.replace(b"record_id,listing_id", b"listing_id,record_id"))
    with pytest.raises(HousingError, match="BOM"):
        parse_csv(b"\xef\xbb\xbf" + data)
    parsed = parse_csv(data.replace(b",10000\n", b",10000.0\n"))
    assert len(parsed.quarantine) == 1 and not parsed.rows


def test_inclusive_raw_price_bounds_precede_ratios_and_keep_empty_months() -> None:
    rows = (
        observation("low", "2026-09", 10000, 1),
        observation("high", "2026-09", 20000, 4),
        observation("outside", "2026-09", 20001, 10000),
    )
    selected = select(snapshot(rows), request(price_min=10000, price_max=20000))
    assert {r.record_id for r in selected.rows} == {"low", "high"}
    assert "2026-08" in selected.available_months
    assert selected.scan_complete


def test_index_omission_differs_from_empty_and_authoritative_strategies_recover() -> None:
    original = snapshot((observation("one", "2026-09", 10000),))
    faulty = original.omit_index_partitions(frozenset({("2026-09", "75001")}))
    initial = select(faulty, request())
    full = select(faulty, request(), "full_csv")
    rebuilt = select(faulty, request(), "rebuilt_index")
    assert not initial.scan_complete and initial.missing_index_partitions == (("2026-09", "75001"),)
    assert not initial.rows
    assert full.scan_complete and rebuilt.scan_complete and full.rows == rebuilt.rows == original.rows
    assert full.selection_sha256 == rebuilt.selection_sha256 != initial.selection_sha256
    assert full.query_sha256 == initial.query_sha256


def test_logical_identity_preserves_multiplicity_but_ignores_order() -> None:
    a, b = observation("a", "2026-09", 10000), observation("b", "2026-09", 10000)
    assert logical_hash((a, b)) == logical_hash((b, a))
    assert logical_hash((a, b)) != logical_hash((a,))


def test_visible_missing_is_error_and_lookback_missing_is_allowed() -> None:
    short = snapshot((), start="2025-10")
    selected = select(short, request())
    assert len(selected.available_months) == 12 and selected.scan_complete
    broken = replace(short, months=short.months[:-1])
    with pytest.raises(HousingError) as error:
        select(broken, request())
    assert error.value.code == "DATA_INCOMPLETE"
