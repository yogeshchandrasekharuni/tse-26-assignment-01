"""Conservative pre-call budget for the pinned Qwen byte-level BPE profile."""

from collections.abc import Mapping, Sequence

from pydantic import JsonValue

from housing.contracts.errors import HousingError
from housing.identity import canonical_json
from housing.replay.capture import semantic_message

CONTEXT_WINDOW = 65536
MAX_COMPLETION = 1024


def context_upper_bound(instruction: str, messages: Sequence[Mapping[str, JsonValue]], tools: object) -> int:
    """One token per UTF-8 byte bounds the pinned gpt2/byte-BPE vocabulary.

    Count even JSON syntax the provider may omit, then reserve 512 tokens per message/tool
    and 4096 for the provider's control/template framing. This deliberately rejects some
    inputs that could fit; it never silently crops history. Overflow is an explicit error.
    """
    payload = canonical_json(
        {"instruction": instruction, "messages": [semantic_message(m) for m in messages], "tools": tools}
    )
    tool_count = len(tools.get("tools", [])) if isinstance(tools, dict) else 0
    return len(payload.encode("utf-8")) + 512 * (len(messages) + tool_count + 1) + 4096


def require_context_budget(bound: int) -> None:
    if bound + MAX_COMPLETION > CONTEXT_WINDOW:
        raise HousingError(
            "BUDGET_EXCEEDED",
            f"Conservative prompt bound {bound} plus completion reserve exceeds {CONTEXT_WINDOW}",
            "context_budget",
        )
