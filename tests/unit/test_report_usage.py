"""Hand-authored provider telemetry: retries, missing fields and cache subsets."""

import json
from pathlib import Path

import pytest

from housing.identity import sha256_bytes
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


def test_declared_interruption_keeps_captured_usage_and_unknown_inflight_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usage_module, "ROOT", tmp_path)
    campaign = tmp_path / "artifacts/campaigns/fixture"
    run = campaign / "cases/a/attempt-001/followup/runs/interrupted"
    model = run / "model"
    model.mkdir(parents=True)
    (campaign / "manifest.json").write_text(json.dumps({"mode": "live"}))
    (model / "000.input.json").write_text(json.dumps({"agent": "orchestrator"}))
    pending = model / "001.input.json"
    pending.write_text(json.dumps({"agent": "reviewer"}))
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
                                        {"prompt": {"total": 5}, "completion": {"total": 2}}
                                    ],
                                }
                            )
                        }
                    ]
                }
            }
        )
    )
    with pytest.raises(ValueError, match="still active"):
        usage_module.campaign_usage(campaign)
    annotation = run.parents[2] / "interruption.json"
    annotation.write_text(
        json.dumps(
            {
                "schema_version": "process-interruption-1",
                "status": "interrupted",
                "observed_at_utc": "2026-10-13T02:41:26+00:00",
                "reason": "user_reported_mac_restart",
                "run_path": str(run.relative_to(tmp_path)),
                "recorded_model_responses": 1,
                "recorded_model_inputs": 2,
                "provider_attempts_for_unanswered_input": None,
                "source_hashes": {
                    str(p.relative_to(tmp_path)): sha256_bytes(p.read_bytes())
                    for p in run.rglob("*")
                    if p.is_file()
                },
            }
        )
    )
    audit = usage_module.campaign_usage(campaign)
    assert audit["physical_runs"] == audit["interrupted_runs_without_terminal"] == 1
    assert audit["recorded_responses"] == audit["reported_provider_attempts"] == 1
    assert audit["recorded_inputs_without_response"] == 1
    assert audit["tokens"]["prompt_total"]["sum_reported"] == 5
    assert audit["tokens"]["completion_total"]["sum_reported"] == 2
    assert audit["runs"][0]["model_decisions"] is None
    assert audit["interruptions"][0]["unanswered_input_provider_usage"] is None
    assert not (run / "terminal.json").exists()
    pending.write_text(json.dumps({"agent": "composer"}))
    with pytest.raises(ValueError, match="inventory or bytes differ"):
        usage_module.campaign_usage(campaign)
