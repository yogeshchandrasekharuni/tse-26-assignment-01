"""Account for available provider telemetry without inventing missing token/request data."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from housing.identity import ROOT, sha256_bytes

TOKEN_FIELDS = {
    "prompt_total": ("prompt", "total"),
    "prompt_cache_read": ("prompt", "cache_read"),
    "prompt_cache_write": ("prompt", "cache_write"),
    "completion_total": ("completion", "total"),
    "completion_reasoning": ("completion", "reasoning"),
}


def nonnegative_integer(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("Provider token/attempt telemetry must be a nonnegative integer or null")
    return value


def response_usage(response: dict[str, Any]) -> dict[str, Any]:
    """Telemetry counts reported attempts; it does not observe network traffic independently."""
    channels = response.get("channels") or {}
    attempts: list[dict[str, Any]] = []
    for block in channels.get("fast-agent-usage", []):
        payload = json.loads(block["text"])
        if payload.get("schema") != "fast-agent.usage/v2":
            raise ValueError("Unrecognized provider usage schema")
        attempts.extend(payload["provider_attempts"])
    retries = 0
    retry_attempts = 0
    for block in channels.get("fast-agent-retry", []):
        payload = json.loads(block["text"])
        if payload.get("schema") != "fast-agent.retry/v1":
            raise ValueError("Unrecognized provider retry schema")
        retry_attempts = max(retry_attempts, nonnegative_integer(payload["provider_attempts"]) or 0)
        retries += len(payload["retries"])
    result: dict[str, Any] = {
        "usage_records": len(attempts),
        "reported_provider_attempts": max(len(attempts), retry_attempts) or None,
        "reported_retries": retries,
    }
    for label, (section, field) in TOKEN_FIELDS.items():
        observed = [nonnegative_integer(attempt.get(section, {}).get(field)) for attempt in attempts]
        known = [value for value in observed if value is not None]
        result[label] = {
            "sum_reported": sum(known) if known else None,
            "records_with_value": len(known),
            "records_without_value": len(observed) - len(known),
        }
    return result


def campaign_usage(directory: Path) -> dict[str, Any]:
    """Scan physical run directories once, retaining failed attempts and avoiding reused-source inflation."""
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / "artifacts/campaigns"):
        raise ValueError("Usage audit requires a registered local campaign")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if manifest["mode"] != "live":
        raise ValueError("Replay responses contain historical usage; audit the live reference instead")
    hashes = {str(manifest_path.relative_to(ROOT)): sha256_bytes(manifest_path.read_bytes())}
    runs: list[dict[str, Any]] = []
    response_count = usage_records = reported_attempts = unknown_attempt_responses = retries = 0
    by_role: Counter[str] = Counter()
    totals: dict[str, dict[str, int | None]] = {
        label: {"sum_reported": None, "records_with_value": 0, "records_without_value": 0}
        for label in TOKEN_FIELDS
    }
    for run in sorted(directory.glob("cases/*/attempt-*/*/runs/*")):
        if not run.is_dir():
            continue
        terminal_path = run / "terminal.json"
        if not terminal_path.is_file():
            raise ValueError(f"Physical run is still active: {run.relative_to(ROOT)}")
        hashes[str(terminal_path.relative_to(ROOT))] = sha256_bytes(terminal_path.read_bytes())
        terminal = json.loads(terminal_path.read_bytes())
        row: dict[str, Any] = {
            "run_path": str(run.relative_to(ROOT)),
            "status": terminal["status"],
            "model_decisions": terminal["model_decisions"],
            "responses": 0,
            "reported_provider_attempts": 0,
            "responses_without_attempt_telemetry": 0,
        }
        for response_path in sorted((run / "model").glob("*.response.json")):
            input_path = response_path.with_name(response_path.name.replace(".response.", ".input."))
            for path in (response_path, input_path):
                hashes[str(path.relative_to(ROOT))] = sha256_bytes(path.read_bytes())
            role = json.loads(input_path.read_bytes())["agent"].split("[", 1)[0]
            by_role[role] += 1
            usage = response_usage(json.loads(response_path.read_bytes()))
            response_count += 1
            row["responses"] += 1
            usage_records += usage["usage_records"]
            retries += usage["reported_retries"]
            if usage["reported_provider_attempts"] is None:
                unknown_attempt_responses += 1
                row["responses_without_attempt_telemetry"] += 1
            else:
                reported_attempts += usage["reported_provider_attempts"]
                row["reported_provider_attempts"] += usage["reported_provider_attempts"]
            for label in TOKEN_FIELDS:
                subtotal = usage[label]
                total = totals[label]
                if subtotal["sum_reported"] is not None:
                    total["sum_reported"] = (total["sum_reported"] or 0) + subtotal["sum_reported"]
                for field in ("records_with_value", "records_without_value"):
                    total[field] = (total[field] or 0) + subtotal[field]
        runs.append(row)
    return {
        "schema_version": "report-provider-usage-1",
        "campaign_id": directory.name,
        "mode": "live_telemetry_audit",
        "physical_runs": len(runs),
        "recorded_responses": response_count,
        "responses_by_role": dict(sorted(by_role.items())),
        "usage_records": usage_records,
        "reported_provider_attempts": reported_attempts,
        "responses_without_attempt_telemetry": unknown_attempt_responses,
        "reported_retries": retries,
        "tokens": totals,
        "cost": "Local inference; monetary cost not assigned",
        "interpretation": (
            "Integer sums of Fast Agent usage/v2 and retry/v1 telemetry from unique physical live runs, "
            "including historical failed attempts. Null means unavailable, never zero. Reported attempts "
            "are not an independent network-traffic measurement. Token sums include repeated prompts; "
            "cache-read tokens are a subset, not additional prompt tokens. Replay is not new inference."
        ),
        "runs": runs,
        "source_hashes": hashes,
    }
