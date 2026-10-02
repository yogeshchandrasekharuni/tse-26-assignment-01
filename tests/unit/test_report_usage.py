"""Hand-authored provider telemetry: retries, missing fields and cache subsets."""

import json
from pathlib import Path

import pytest

from housing.reporting import usage as usage_module
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


def test_physical_audit_preserves_unknown_failed_calls_and_rejects_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usage_module, "ROOT", tmp_path)
    campaign = tmp_path / "artifacts/campaigns/fixture"
    model = campaign / "cases/a/attempt-001/source/runs/failed/model"
    model.mkdir(parents=True)
    manifest = campaign / "manifest.json"
    manifest.write_text(json.dumps({"mode": "live"}))
    (model.parent / "terminal.json").write_text(json.dumps({"status": "failed", "model_decisions": 3}))
    for index, role in enumerate(("orchestrator", "price", "reviewer")):
        (model / f"{index:03}.input.json").write_text(json.dumps({"agent": role}))
    (model / "000.response.json").write_text(
        json.dumps(
            {
                "channels": {
                    "fast-agent-usage": [
                        {
                            "text": json.dumps(
                                {
                                    "schema": "fast-agent.usage/v2",
                                    "provider_attempts": [
                                        {"prompt": {"total": 100}, "completion": {"total": 10}}
                                    ],
                                }
                            )
                        }
                    ]
                }
            }
        )
    )
    (model / "001.response.json").write_text(json.dumps({"content": []}))
    audit = usage_module.campaign_usage(campaign)
    assert audit["physical_runs"] == 1
    assert audit["recorded_responses"] == 2
    assert audit["reported_provider_attempts"] == 1
    assert audit["responses_without_attempt_telemetry"] == 1
    assert audit["recorded_inputs_without_response"] == 1
    assert str((model / "002.input.json").relative_to(tmp_path)) in audit["source_hashes"]
    assert audit["tokens"]["prompt_total"]["sum_reported"] == 100
    assert audit["tokens"]["completion_total"]["sum_reported"] == 10
    manifest.write_text(json.dumps({"mode": "replay"}))
    with pytest.raises(ValueError, match="historical usage"):
        usage_module.campaign_usage(campaign)
