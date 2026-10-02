"""Hand-authored provider telemetry: retries, missing fields and cache subsets."""

import json

import pytest

from housing.reporting.usage import response_usage


def test_reported_retry_attempts_and_missing_tokens_stay_distinct() -> None:
    response = {
        "channels": {
            "fast-agent-usage": [
                {
                    "text": json.dumps(
                        {
                            "schema": "fast-agent.usage/v2",
                            "provider_attempts": [
                                {"prompt": {"total": 100, "cache_read": 60}, "completion": {"total": 12}},
                                {"prompt": {"total": 80, "cache_read": None}, "completion": {"total": 5}},
                            ],
                        }
                    )
                }
            ],
            "fast-agent-retry": [
                {
                    "text": json.dumps(
                        {"schema": "fast-agent.retry/v1", "provider_attempts": 3, "retries": [{}, {}]}
                    )
                }
            ],
        }
    }
    audit = response_usage(response)
    assert audit["reported_provider_attempts"] == 3
    assert audit["reported_retries"] == 2
    assert audit["prompt_total"]["sum_reported"] == 180
    assert audit["completion_total"]["sum_reported"] == 17
    assert audit["prompt_cache_read"] == {
        "sum_reported": 60,
        "records_with_value": 1,
        "records_without_value": 1,
    }
    assert audit["completion_reasoning"]["sum_reported"] is None
    assert response_usage({})["reported_provider_attempts"] is None


def test_malformed_provider_numbers_are_not_coerced() -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        response_usage(
            {
                "channels": {
                    "fast-agent-usage": [
                        {
                            "text": json.dumps(
                                {
                                    "schema": "fast-agent.usage/v2",
                                    "provider_attempts": [{"prompt": {"total": 1.5}}],
                                }
                            )
                        }
                    ]
                }
            }
        )
