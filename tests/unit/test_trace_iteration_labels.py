"""Pass annotations need causal witnesses and never replace arbitrary raw tags."""

from copy import deepcopy

from pydantic import JsonValue

from housing.observability.iterations import iteration_labels


def test_a_plan_alone_does_not_relabel_an_unrelated_or_ambiguous_repair() -> None:
    events: list[dict[str, JsonValue]] = [
        {"event": "PLAN_DECIDED", "iteration": 1, "payload": {"plan": {"version": 1}}},
        {
            "event": "AGENT_DECISION",
            "actor": "price",
            "iteration": 1,
            "payload": {"valid": False},
        },
        {"event": "AGENT_REPAIR", "actor": "supply", "iteration": 0, "payload": {}},
        {
            "event": "AGENT_DECISION",
            "actor": "price",
            "iteration": 0,
            "payload": {"valid": False},
        },
        {"event": "AGENT_REPAIR", "actor": "price", "iteration": 0, "payload": {}},
        {"event": "AGGREGATE_COMPLETED", "actor": "aggregator", "iteration": 0, "payload": {}},
    ]
    original = deepcopy(events)
    labels = iteration_labels(events)
    assert [label.display_iteration for label in labels] == [1, 1, 0, 0, 0, 0]
    assert all(label.basis == "recorded" for label in labels)
    assert events == original
