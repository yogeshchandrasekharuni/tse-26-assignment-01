"""Mutate a genuine development capture in memory; never fabricate live responses."""

import copy

import pytest
from pydantic import JsonValue

from housing.agents.context import context_upper_bound, require_context_budget
from housing.contracts.errors import HousingError
from housing.identity import ROOT
from housing.replay.capture import Cassette, semantic_message

CAPTURE = ROOT / "artifacts/traces/20261001T150456Z-6c0cbee2b9/cassettes/000.json"


def test_genuine_cassette_integrity_and_exact_semantic_fields() -> None:
    packet = Cassette.model_validate_json(CAPTURE.read_bytes())
    packet.verify(packet.input, packet.boundary_sha256)
    for field in (
        "agent",
        "messages",
        "message_tool_call_order",
        "instruction",
        "tools",
        "context",
        "model_profile",
        "requested_seed",
        "effective_seed",
        "role_schema_sha256",
        "prompt_bundle_sha256",
        "boundary_sha256",
    ):
        changed = copy.deepcopy(packet.input)
        changed[field] = "deliberate mismatch control"
        with pytest.raises(HousingError) as error:
            packet.verify(changed, packet.boundary_sha256)
        assert error.value.code == "REPLAY_MISS"
    corrupt = packet.model_copy(update={"response_sha256": "0" * 64})
    with pytest.raises(HousingError):
        corrupt.verify(packet.input, packet.boundary_sha256)


def test_tool_call_order_is_integrity_protected() -> None:
    packet = Cassette.model_validate_json(CAPTURE.with_name("001.json").read_bytes())
    assert len(packet.response_tool_call_order) == 2
    packet.verify(packet.input, packet.boundary_sha256)
    reversed_order = packet.model_copy(
        update={"response_tool_call_order": packet.response_tool_call_order[::-1]}
    )
    with pytest.raises(HousingError):
        reversed_order.verify(packet.input, packet.boundary_sha256)


def test_only_verified_audit_fields_are_excluded() -> None:
    first: dict[str, JsonValue] = {
        "role": "assistant",
        "timestamp": "first",
        "content": [],
        "channels": {"fast-agent-timing": [], "reasoning": ["retain exact reasoning"]},
    }
    other: dict[str, JsonValue] = {
        **first,
        "timestamp": "second",
        "channels": {"reasoning": ["retain exact reasoning"]},
    }
    assert semantic_message(first) == semantic_message(other)
    assert semantic_message(other) != semantic_message({**other, "channels": {"reasoning": ["changed"]}})


def test_context_overflow_is_explicit_before_inference() -> None:
    require_context_budget(
        context_upper_bound("short instruction", [{"role": "user", "content": "small"}], {})
    )
    bound = context_upper_bound("instruction", [{"role": "user", "content": "x" * 80000}], {})
    with pytest.raises(HousingError) as failure:
        require_context_budget(bound)
    assert failure.value.code == "BUDGET_EXCEEDED"
