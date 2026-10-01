from datetime import datetime
from fractions import Fraction

import pytest
from conftest import request
from pydantic import ValidationError

from housing.contracts.decisions import PlanDecision, ReviewDecision
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.identity import ROOT, semantic_hash
from housing.tools.calendar import add_month, month_range, utc_month
from housing.tools.exact import median, percentage, round_half_even, serial


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (Fraction(1, 2_000_000), "0.000000"),
        (Fraction(3, 2_000_000), "0.000002"),
        (Fraction(-1, 2_000_000), "0.000000"),
        (Fraction(-3, 2_000_000), "-0.000002"),
        (Fraction(19999999, 2_000_000), "10.000000"),
        (Fraction(1, 3), "0.333333"),
    ],
)
def test_exact_rounding(raw: Fraction, expected: str) -> None:
    assert serial(raw) == expected


def test_even_median_half_cent_and_zero_denominators() -> None:
    assert median([Fraction(10000, 100), Fraction(10001, 100)]) == Fraction(20001, 200)
    assert median([Fraction(3), Fraction(1), Fraction(2)]) == 2
    assert median([]) is None
    assert round_half_even(Fraction(-5, 2)) == -2
    assert round_half_even(Fraction(-7, 2)) == -4
    assert serial(percentage(0, 5)) == "-100.000000"
    assert percentage(5, 0) is None
    assert percentage(0, 0) is None
    assert percentage(None, 10) is None
    with pytest.raises(TypeError):
        serial(1.25)  # type: ignore[arg-type]


def test_calendar_uses_months_and_utc_boundaries() -> None:
    assert add_month("2024-02", -12) == "2023-02"
    assert add_month("2025-12", 1) == "2026-01"
    assert month_range("2025-12", "2026-02") == ("2025-12", "2026-01", "2026-02")
    assert utc_month("2024-03-01T00:15:00+05:30") == "2024-02"
    assert utc_month("2024-02-29T23:30:00-01:00") == "2024-03"
    with pytest.raises(ValueError):
        utc_month(datetime(2024, 2, 29).isoformat())
    with pytest.raises(ValueError):
        add_month("0001-01", -1)


def test_request_is_strict_normalized_and_immutable() -> None:
    payload = request(zips=("75006", "75001", "75006")).model_dump(mode="json")
    parsed = AnalysisRequest.model_validate(payload)
    assert parsed.criteria.zips == ("75001", "75006")
    assert len(parsed.required_months) == 24
    assert parsed.visible_months[0] == "2025-10"
    assert parsed.required_months[0] == "2024-10"
    with pytest.raises(ValidationError):
        parsed.criteria.bedrooms_min = 2
    payload["criteria"]["bedrooms_min"] = True
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(payload)
    payload = request().model_dump(mode="json")
    payload["criteria"]["price_min_cents"] = "100"
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(payload)
    payload = request().model_dump(mode="json")
    payload["criteria"]["extra"] = "ignored?"
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(payload)


def test_display_and_seed_do_not_change_housing_query() -> None:
    source = request()
    payload = source.model_dump(mode="json")
    payload["display"] = {"money": "USD_THOUSANDS", "area": "SQM"}
    payload["seed"] = 130363
    followup = AnalysisRequest.model_validate(payload)
    assert source.housing_query("a" * 64) == followup.housing_query("a" * 64)
    assert semantic_hash(source) != semantic_hash(followup)


def test_agent_duplicates_are_invalid_rather_than_silently_repaired() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision.model_validate(
            {
                "role": "reviewer",
                "decision_type": "review",
                "decision": "ACCEPT",
                "signals": ["COMPLETE_SUPPORT", "COMPLETE_SUPPORT"],
                "requested_action": None,
            }
        )
    with pytest.raises(ValidationError):
        PlanDecision.model_validate(
            {
                "role": "orchestrator",
                "decision_type": "plan",
                "action": "INITIAL",
                "scan_strategy": "indexed",
                "specialists": ["price", "supply", "price"],
                "region_purpose": "none",
                "reason_codes": [],
            }
        )


def test_handoff_output_example_satisfies_new_contract() -> None:
    output = AnalysisOutput.model_validate_json(
        (ROOT / "housing-tse-codex-handoff/fixtures/example_output.json").read_bytes()
    )
    assert output.canonical.summary.total_observations == 24
