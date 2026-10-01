"""Auxiliary policy tests; these do not count as observed live MAS outcomes."""

import hashlib
import json
import socket
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from probe_fast_agent import PriceIntent
from probe_support import Evidence, deny_network, digest, match_cassette, write_json
from probe_tools import ProbeTools, ReviewDecision
from probe_tool_playback import semantic_messages


def test_replay_requires_every_semantic_input_and_response_integrity(tmp_path):
    basis = {"prompt": "request price tool", "schema": "v1", "seed": 104729, "receipt": "original"}
    response = '{"tool":"price_stats"}'
    path = tmp_path / f"{digest(basis)}.json"
    cassette = {"origin": "live_captured", "key_basis": basis, "raw_response_text": response,
                "raw_response_sha256": hashlib.sha256(response.encode()).hexdigest()}
    write_json(path, cassette)
    assert match_cassette(tmp_path, basis)["raw_response_text"] == response
    for field in basis:
        with pytest.raises(ValueError, match="REPLAY_MISS"):
            match_cassette(tmp_path, {**basis, field: "changed"})
    cassette["raw_response_text"] = "altered"
    write_json(path, cassette)
    with pytest.raises(ValueError, match="corrupt response"):
        match_cassette(tmp_path, basis)
    cassette["raw_response_text"] = response
    cassette["origin"] = "policy_simulation"
    write_json(path, cassette)
    with pytest.raises(ValueError, match="lineage"):
        match_cassette(tmp_path, basis)


def test_model_cannot_add_filters_or_change_role():
    valid = {"role": "price", "decision_type": "tool_intent", "tool": "price_stats",
             "partition_order": "month_asc", "purpose": "statistics"}
    for change in [{"price_min_cents": 0}, {"role": "supply"}, {"tool": "shell"}]:
        with pytest.raises(ValidationError):
            PriceIntent.model_validate({**valid, **change})
    with pytest.raises(ValidationError):
        ReviewDecision(role="reviewer", decision="REFINE", requested_action="WIDEN_PRICE_BAND")


def test_refinement_changes_executed_scan_and_region_with_immutable_query(tmp_path):
    tools = ProbeTools(Evidence(tmp_path / "policy-test"))
    original_query = json.loads(json.dumps(tools.query))
    with pytest.raises(ValueError, match="not activated"):
        tools.scan_region()
    with pytest.raises(ValueError, match="before acceptance"):
        tools.compose_report(["observations", "support"])
    tools.scan_price()
    initial = tools.scan_supply()
    assert initial["result"]["monthly_counts"]["2026-03"] == 0
    with pytest.raises(ValueError, match="mismatch cannot be accepted"):
        tools.submit_review("ACCEPT_LIMITED")
    tools.submit_review("REFINE", "EXACT_RESCAN_WITH_REGION")
    with pytest.raises(ValueError, match="both specialist receipts required"):
        tools.inspect_coverage()
    tools.scan_price()
    final = tools.scan_supply()
    tools.scan_region()
    tools.submit_review("ACCEPT_LIMITED")
    assert final["result"]["monthly_counts"]["2026-03"] == 2
    assert tools.query == original_query
    assert tools.plans == [{"strategy": "indexed", "active": ["price", "supply"]},
                           {"strategy": "full_csv", "active": ["price", "supply", "region"]}]
    assert tools.compose_report(["observations", "support"])["total_observations"] == 24


def test_offline_guard_blocks_connections_before_transport():
    with deny_network() as attempts:
        with pytest.raises(OSError, match="OFFLINE"):
            socket.create_connection(("127.0.0.1", 11434))
        assert len(attempts) == 1


def test_replay_projection_ignores_only_framework_audit_metadata():
    original = [{"role": "user", "content": [], "tool_results": {"call": {"value": 22}},
                 "timestamp": "first", "channels": {"fast-agent-tool-timing": ["fast"],
                                                        "reasoning": ["retain this"]}}]
    changed_audit = json.loads(json.dumps(original))
    changed_audit[0]["timestamp"] = "second"
    changed_audit[0]["channels"]["fast-agent-tool-timing"] = ["slow"]
    assert semantic_messages(original) == semantic_messages(changed_audit)
    changed_result = json.loads(json.dumps(original))
    changed_result[0]["tool_results"]["call"]["value"] = 24
    assert semantic_messages(original) != semantic_messages(changed_result)
    changed_reasoning = json.loads(json.dumps(original))
    changed_reasoning[0]["channels"]["reasoning"] = ["different"]
    assert semantic_messages(original) != semantic_messages(changed_reasoning)
