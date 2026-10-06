"""Annotate a known default-zero repair tag without rewriting captured events."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue

type IterationBasis = Literal["recorded", "plan_and_invalid_decision"]


@dataclass(frozen=True)
class IterationLabel:
    display_iteration: int
    basis: IterationBasis


def natural(value: JsonValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Trace iteration must be a nonnegative integer")
    return value


def iteration_labels(events: Sequence[dict[str, JsonValue]]) -> tuple[IterationLabel, ...]:
    """Require the active plan and preceding invalid decision to agree on a correction.

    Other event tags remain exactly as recorded. This is a read-side annotation,
    not a repair of the raw trace or an inference from the number of model calls.
    """
    active_plan: int | None = None
    previous: dict[str, JsonValue] | None = None
    labels: list[IterationLabel] = []
    for event in events:
        recorded = natural(event.get("iteration"))
        payload = event.get("payload")
        if event.get("event") == "PLAN_DECIDED" and isinstance(payload, dict):
            plan = payload.get("plan")
            if isinstance(plan, dict):
                active_plan = natural(plan.get("version"))
        display = recorded
        basis: IterationBasis = "recorded"
        if (
            event.get("event") == "AGENT_REPAIR"
            and recorded == 0
            and active_plan is not None
            and active_plan > 0
            and previous is not None
            and previous.get("event") == "AGENT_DECISION"
            and previous.get("actor") == event.get("actor")
            and previous.get("iteration") == active_plan
        ):
            previous_payload = previous.get("payload")
            if isinstance(previous_payload, dict) and previous_payload.get("valid") is False:
                display, basis = active_plan, "plan_and_invalid_decision"
        labels.append(IterationLabel(display, basis))
        previous = event
    return tuple(labels)
