"""Exact, integrity-checked model-response cassettes; never cached analysis answers."""

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import JsonValue

from housing.contracts.common import FrozenModel, NonnegativeInt, Sha256
from housing.contracts.errors import HousingError
from housing.identity import semantic_hash, write_json

AUDIT_CHANNELS = frozenset({"fast-agent-timing", "fast-agent-usage", "fast-agent-tool-timing"})


def semantic_message(original: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Only framework audit fields are excluded. Calls, arguments, reasoning and results remain exact."""
    message = {k: v for k, v in original.items() if k != "timestamp"}
    channels = message.get("channels")
    if isinstance(channels, dict):
        filtered = {k: v for k, v in channels.items() if k not in AUDIT_CHANNELS}
        if filtered:
            message["channels"] = filtered
        else:
            message.pop("channels")
    return message


def semantic_input(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
        raise HousingError("REPLAY_MISS", "Invalid captured message list", "cassette_match")
    return {**payload, "messages": [semantic_message(m) for m in messages if isinstance(m, dict)]}


class Cassette(FrozenModel):
    schema_version: Literal["production-capture-2"]
    origin: Literal["live_captured"]
    sequence: NonnegativeInt
    boundary_sha256: Sha256
    semantic_input_sha256: Sha256
    raw_input_sha256: Sha256
    input: dict[str, JsonValue]
    response_sha256: Sha256
    response_tool_call_order: tuple[str, ...]
    response: dict[str, JsonValue]

    def verify(self, actual: dict[str, JsonValue], boundary_hash: str) -> None:
        calls = self.response.get("tool_calls")
        call_ids = set(calls) if isinstance(calls, dict) else set()
        if (
            self.boundary_sha256 != boundary_hash
            or self.raw_input_sha256 != semantic_hash(self.input)
            or self.response_sha256
            != semantic_hash({"message": self.response, "tool_call_order": self.response_tool_call_order})
            or (calls is not None and not isinstance(calls, dict))
            or set(self.response_tool_call_order) != call_ids
            or len(self.response_tool_call_order) != len(set(self.response_tool_call_order))
            or self.semantic_input_sha256 != semantic_hash(semantic_input(self.input))
            or self.semantic_input_sha256 != semantic_hash(semantic_input(actual))
        ):
            raise HousingError(
                "REPLAY_MISS",
                "Exact semantic input, source boundary or cassette integrity differs",
                "cassette_match",
            )


def save_cassette(
    directory: Path,
    sequence: int,
    boundary_hash: str,
    payload: dict[str, JsonValue],
    response: dict[str, JsonValue],
) -> None:
    calls = response.get("tool_calls")
    order = tuple(calls) if isinstance(calls, dict) else ()
    packet = Cassette(
        schema_version="production-capture-2",
        origin="live_captured",
        sequence=sequence,
        boundary_sha256=boundary_hash,
        semantic_input_sha256=semantic_hash(semantic_input(payload)),
        raw_input_sha256=semantic_hash(payload),
        input=payload,
        response_sha256=semantic_hash({"message": response, "tool_call_order": order}),
        response_tool_call_order=order,
        response=response,
    )
    write_json(directory / "cassettes" / f"{sequence:03d}.json", packet)


def load_cassettes(directory: Path) -> tuple[Cassette, ...]:
    from pydantic import ValidationError

    try:
        packets = tuple(
            Cassette.model_validate_json(p.read_bytes())
            for p in sorted((directory / "cassettes").glob("*.json"))
        )
        if not packets or tuple(p.sequence for p in packets) != tuple(range(len(packets))):
            raise ValueError("Missing or noncontiguous cassette sequence")
        for packet in packets:
            packet.verify(packet.input, packet.boundary_sha256)
        return packets
    except (OSError, ValueError, ValidationError) as error:
        raise HousingError(
            "REPLAY_MISS", f"Capture corpus unavailable or invalid: {error}", "cassette_load"
        ) from error
