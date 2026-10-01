"""Auxiliary controller tests. Scripted role decisions are never empirical MAS evidence."""

import json
from pathlib import Path

import pytest
from conftest import observation, request, snapshot

import housing.workflow.controller as workflow
from housing.contracts.decisions import PriceDecision, RegionDecision, SupplyDecision
from housing.contracts.errors import HousingError
from housing.contracts.stats import ToolExecution, WorkflowPlan
from housing.data.store import Selection
from housing.identity import canonical_json
from housing.workflow.controller import Controller, Role


def plan(action: str = "INITIAL", *, region: bool = False, reasons: tuple[str, ...] = ()) -> str:
    return canonical_json(
        {
            "role": "orchestrator",
            "decision_type": "plan",
            "action": action,
            "scan_strategy": {
                "INITIAL": "indexed",
                "EXACT_RESCAN_WITH_REGION": "full_csv",
                "REBUILD_INDEX_AND_RESCAN": "rebuilt_index",
            }[action],
            "specialists": ["price", "supply", "region"] if region else ["price", "supply"],
            "region_purpose": "coverage_diagnostic" if region else "none",
            "reason_codes": reasons,
        }
    )


def scans(controller: Controller, *, region: bool = False) -> None:
    roles: tuple[Role, ...] = ("price", "supply", "region") if region else ("price", "supply")
    for role in roles:
        controller.submit(
            role,
            canonical_json(
                {
                    "role": role,
                    "decision_type": "tool_intent",
                    "tool": f"{role}_stats",
                    "partition_order": "month_asc",
                    "purpose": "coverage_diagnostic" if role == "region" else "statistics",
                }
            ),
        )


def review(controller: Controller, decision: str, action: str | None = None) -> None:
    controller.submit(
        "reviewer",
        canonical_json(
            {
                "role": "reviewer",
                "decision_type": "review",
                "decision": decision,
                "signals": controller.signals(),
                "requested_action": action,
            }
        ),
    )


def test_omission_loop_changes_real_tool_path_and_keeps_query(tmp_path: Path) -> None:
    original = snapshot((observation("one", "2026-09", 10000),))
    faulty = original.omit_index_partitions(frozenset({("2026-09", "75001")}))
    c = Controller(request(), faulty, tmp_path, "policy-test", "policy_simulation", "a" * 64)
    c.submit("orchestrator", plan())
    scans(c)
    assert c.canonical is not None and c.canonical.summary.total_observations == 0
    query = c.query_hash
    review(c, "REFINE", "EXACT_RESCAN_WITH_REGION")
    c.submit("orchestrator", plan("EXACT_RESCAN_WITH_REGION", region=True, reasons=c.signals()))
    scans(c, region=True)
    assert c.query_hash == query and c.selection is not None and c.selection.strategy == "full_csv"
    assert c.canonical.summary.total_observations == 1
    review(c, "ACCEPT_LIMITED")
    c.submit(
        "composer",
        canonical_json(
            {
                "role": "composer",
                "decision_type": "report",
                "fact_ids": ["observations"],
                "caveat_codes": c.caveats(),
            }
        ),
    )
    ack = c.finalize()
    assert ack["total_observations"] == 1 and c.output is not None
    assert c.output.quality.status == "limited" and c.output.metadata.seed_support == "unsupported"
    assert c.output.narrative.fact_ids == ("observations",)
    assert "Synthetic Dallas-themed test feed" in c.output.narrative.text
    events = [json.loads(line) for line in c.trace.path.read_text().splitlines()]
    changed = next(e for e in events if e["event"] == "REFINEMENT_APPLIED")["payload"]
    assert changed["strategy_changed"] and changed["active_specialists_changed"]
    assert changed["criteria_hash_before"] == changed["criteria_hash_after"]
    routes = [
        (e["actor"], e["payload"]["receipt"]["strategy"]) for e in events if e["event"] == "TOOL_COMPLETED"
    ]
    assert routes == [
        ("price", "indexed"),
        ("supply", "indexed"),
        ("price", "full_csv"),
        ("supply", "full_csv"),
        ("region", "full_csv"),
    ]


def test_early_review_fails_closed(tmp_path: Path) -> None:
    c = Controller(request(), snapshot(()), tmp_path, "early-review", "policy_simulation", "a" * 64)
    c.submit("orchestrator", plan())
    with pytest.raises(HousingError, match="not permitted"):
        review(c, "ACCEPT")
    assert c.fatal is not None and c.output is None


def test_exactly_one_explicit_schema_repair_and_no_policy_repair(tmp_path: Path) -> None:
    c = Controller(request(), snapshot(()), tmp_path, "repair", "policy_simulation", "a" * 64)
    result = c.submit("orchestrator", "not json")
    assert result["status"] == "repair_required" and c.repairs_used == 1
    c.submit("orchestrator", plan())
    with pytest.raises(HousingError) as failure:
        c.submit("price", "not json")
    assert failure.value.code == "AGENT_OUTPUT_INVALID"


def test_sparsity_requires_rescan_and_cannot_be_accepted_as_complete(tmp_path: Path) -> None:
    c = Controller(request(), snapshot(()), tmp_path, "wrong-review", "policy_simulation", "a" * 64)
    c.submit("orchestrator", plan())
    scans(c)
    with pytest.raises(HousingError, match="violates"):
        review(c, "ACCEPT")
    assert c.output is None


def test_only_new_receipt_signal_allows_second_distinct_refinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = Controller(request(), snapshot(()), tmp_path, "two-refinements", "policy_simulation", "a" * 64)
    original_dispatch = workflow.dispatch

    def injected_dispatch(
        selection: Selection,
        current: WorkflowPlan,
        decision: PriceDecision | SupplyDecision | RegionDecision,
        run_id: str,
        artifacts: Path,
    ) -> ToolExecution:
        execution = original_dispatch(selection, current, decision, run_id, artifacts)
        if current.version == 1 and decision.role == "supply":
            bad = execution.receipt.model_copy(update={"selection_sha256": "f" * 64})
            return execution.model_copy(update={"receipt": bad})
        return execution

    monkeypatch.setattr(workflow, "dispatch", injected_dispatch)
    c.submit("orchestrator", plan())
    scans(c)
    review(c, "REFINE", "EXACT_RESCAN_WITH_REGION")
    c.submit("orchestrator", plan("EXACT_RESCAN_WITH_REGION", region=True, reasons=c.signals()))
    scans(c, region=True)
    assert c.canonical is None and c.signals() == ("RECEIPT_MISMATCH",)
    review(c, "REFINE", "REBUILD_INDEX_AND_RESCAN")
    c.submit("orchestrator", plan("REBUILD_INDEX_AND_RESCAN", region=True, reasons=c.signals()))
    scans(c, region=True)
    assert c.plan is not None and c.plan.version == 2 and c.plan.scan_strategy == "rebuilt_index"
    review(c, "ACCEPT_LIMITED")
    assert len(c.seen_plans) == 3 and c.stage == "ACCEPTED"


def test_repair_reports_the_cross_field_constraint_and_preserves_invalid_attempt(tmp_path: Path) -> None:
    c = Controller(request(), snapshot(()), tmp_path, "repair-detail", "policy_simulation", "a" * 64)
    bad = json.loads(plan())
    bad["action"] = "EXACT_RESCAN_WITH_REGION"
    result = c.submit("orchestrator", canonical_json(bad))
    assert result["status"] == "repair_required"
    assert "Plan action and scan strategy disagree" in canonical_json(result["errors"])
    assert result["planning_constraints"] == c.planning_constraints()
    assert c.stage == "PLAN_REQUIRED" and c.plan is None
