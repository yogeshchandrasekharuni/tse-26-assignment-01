"""Small guarded state machine inside the public Orchestrator boundary."""

from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from housing.contracts.common import FrozenModel, Mode, Signal
from housing.contracts.decisions import (
    ROLE_DECISION,
    FinalizeDecision,
    PlanDecision,
    PriceDecision,
    RegionDecision,
    ReportDecision,
    ReviewDecision,
    SupplyDecision,
)
from housing.contracts.errors import HousingError
from housing.contracts.output import AnalysisOutput, Canonical, Metadata, Narrative, Quality
from housing.contracts.request import AnalysisRequest
from housing.contracts.stats import ToolExecution, WorkflowPlan
from housing.data.store import Selection, Snapshot, select
from housing.identity import ROOT, semantic_hash, write_json
from housing.tools.aggregate import aggregate, present
from housing.tools.statistics import dispatch
from housing.workflow.trace import Trace

type Role = Literal["orchestrator", "price", "supply", "region", "reviewer", "composer"]


class Controller:
    def __init__(
        self,
        request: AnalysisRequest,
        snapshot: Snapshot,
        directory: Path,
        run_id: str,
        mode: Mode,
        prompt_hash: str,
    ):
        self.request, self.snapshot, self.directory = request, snapshot, directory
        self.run_id, self.mode, self.prompt_hash = run_id, mode, prompt_hash
        self.query_hash = semantic_hash(request.housing_query(snapshot.view_sha256))
        self.trace = Trace(directory, run_id, mode, self.query_hash, snapshot.view_sha256)
        self.stage = "PLAN_REQUIRED"
        self.plan: WorkflowPlan | None = None
        self.selection: Selection | None = None
        self.executions: dict[str, ToolExecution] = {}
        self.canonical: Canonical | None = None
        self.review: ReviewDecision | None = None
        self.review_sequence: int | None = None
        self.narrative: Narrative | None = None
        self.output: AnalysisOutput | None = None
        self.fatal: HousingError | None = None
        self.repairs_used = 0
        self.repair_role: Role | None = None
        self.repair_details: dict[str, object] | None = None
        self.seen_plans: set[str] = set()
        self.seen_review_signals: set[Signal] = set()
        self.receipt_mismatch = False
        self.trace.emit(
            "RUN_STARTED",
            "controller",
            {
                "request_sha256": semantic_hash(request),
                "snapshot_sha256": snapshot.source_sha256,
                "index_sha256": snapshot.index_sha256,
                "prompt_bundle_sha256": prompt_hash,
                "source_kind": "synthetic",
                "injected_index_omissions": tuple(
                    (m, z) for m in snapshot.months for z in snapshot.zips if (m, z) not in snapshot.index
                ),
                "headline_eligible": mode != "policy_simulation"
                and all((m, z) in snapshot.index for m in snapshot.months for z in snapshot.zips),
            },
        )
        write_json(directory / "request.json", request)

    def abort(
        self,
        message: str,
        code: Literal["AGENT_POLICY_ERROR", "AGENT_OUTPUT_INVALID", "BUDGET_EXCEEDED"] = "AGENT_POLICY_ERROR",
    ) -> None:
        self.fatal = HousingError(code, message, self.stage)
        raise self.fatal

    def guard(self, role: Role) -> None:
        if self.fatal:
            raise self.fatal
        if self.repair_role is not None and self.repair_role != role:
            self.abort("Schema repair must finish in the role that produced invalid JSON")
        permitted = (
            self.stage == "PLAN_REQUIRED"
            and role == "orchestrator"
            or self.stage == "SCANNING"
            and self.plan is not None
            and role in self.plan.active_specialists
            and role not in self.executions
            or self.stage == "REVIEW_REQUIRED"
            and role == "reviewer"
            or self.stage == "ACCEPTED"
            and role == "composer"
        )
        if not permitted:
            self.abort(f"Role {role} is not permitted during {self.stage}")

    def validate_decision[T: FrozenModel](self, role: Role, raw: str, adapter: TypeAdapter[T]) -> T | None:
        try:
            decision = adapter.validate_json(raw)
        except ValidationError as error:
            errors = [
                {"location": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in error.errors()
            ]
            self.trace.emit(
                "AGENT_DECISION",
                role,
                {"valid": False, "raw": raw, "errors": errors},
                iteration=self.plan.version if self.plan else 0,
            )
            if self.repairs_used:
                self.abort("The one explicit schema repair was exhausted", "AGENT_OUTPUT_INVALID")
            self.repairs_used += 1
            self.repair_role = role
            self.repair_details = {"role": role, "invalid_response": raw, "errors": errors}
            self.trace.emit(
                "AGENT_REPAIR",
                role,
                {
                    "repair": 1,
                    "errors": errors,
                    "instruction": "Return a corrected object using the same immutable context",
                },
            )
            return None
        if getattr(decision, "role", None) != role:
            self.abort("A role cannot submit another role's decision")
        self.repair_role = None
        self.repair_details = None
        self.trace.emit(
            "AGENT_DECISION",
            role,
            {"valid": True, "decision": decision, "decision_sha256": semantic_hash(decision)},
            iteration=self.plan.version if self.plan else 0,
        )
        return decision

    def repair_response(self, role: Role) -> dict[str, object]:
        return {
            "status": "repair_required",
            "errors": self.repair_details["errors"] if self.repair_details else [],
            "remaining_repairs": 0,
            "planning_constraints": self.planning_constraints()
            if role == "orchestrator" and self.stage == "PLAN_REQUIRED"
            else None,
        }

    def submit_finalization(self, raw: str) -> dict[str, object]:
        if self.fatal:
            raise self.fatal
        if self.stage != "COMPOSED":
            self.abort("Parent ended before accepted composition")
        decision = self.validate_decision("orchestrator", raw, TypeAdapter(FinalizeDecision))
        return self.finalize() if decision is not None else self.repair_response("orchestrator")

    def submit(self, role: Role, raw: str) -> dict[str, object]:
        self.guard(role)
        decision = self.validate_decision(role, raw, ROLE_DECISION)
        if decision is None:
            return self.repair_response(role)
        try:
            if isinstance(decision, PlanDecision):
                self.apply_plan(decision)
            elif isinstance(decision, (PriceDecision, SupplyDecision, RegionDecision)):
                self.scan(decision)
            elif isinstance(decision, ReviewDecision):
                self.apply_review(decision)
            elif isinstance(decision, ReportDecision):
                self.compose(decision)
        except HousingError as error:
            self.fatal = error
            raise
        return {
            "status": "decision_applied",
            "role": role,
            "decision_sha256": semantic_hash(decision),
            "stage": self.stage,
            "iteration": self.plan.version if self.plan else 0,
            "scan_strategy": self.plan.scan_strategy if self.plan else None,
            "active_specialists": self.plan.active_specialists if self.plan else (),
            "completed_specialists": tuple(sorted(self.executions)),
            "semantic_receipt_hashes": {
                k: e.receipt.semantic_sha256 for k, e in sorted(self.executions.items())
            },
            "signals": self.signals(),
            "next_action": self.review.requested_action
            if self.review and self.stage == "PLAN_REQUIRED"
            else None,
            "planning_constraints": self.planning_constraints() if self.stage == "PLAN_REQUIRED" else None,
        }

    def apply_plan(self, decision: PlanDecision) -> None:
        previous = self.plan
        version = previous.version + 1 if previous else 0
        expected_action = self.review.requested_action if self.review else "INITIAL"
        if version > 2:
            self.abort("Maximum two semantic refinements", "BUDGET_EXCEEDED")
        if decision.action != expected_action:
            self.abort("Plan action does not implement the actual preceding review")
        if set(decision.reason_codes) != set(self.review.signals if self.review else ()):
            self.abort("Plan reasons must match its actual triggering review")
        expected_purpose = (
            "public_comparison"
            if self.request.compare_regions
            else ("coverage_diagnostic" if version else "none")
        )
        expected_roles = {"price", "supply"} | ({"region"} if expected_purpose != "none" else set())
        if set(decision.specialists) != expected_roles or decision.region_purpose != expected_purpose:
            self.abort("Plan must preserve mandatory roles, public comparison and refinement diagnosis")
        signature = semantic_hash(
            {
                "strategy": decision.scan_strategy,
                "specialists": sorted(decision.specialists),
                "region_purpose": decision.region_purpose,
            }
        )
        if signature in self.seen_plans:
            self.abort("A refinement cannot repeat the same execution plan", "BUDGET_EXCEEDED")
        self.seen_plans.add(signature)
        self.plan = WorkflowPlan(
            version=version,
            canonical_query_sha256=self.query_hash,
            dataset_view_sha256=self.snapshot.view_sha256,
            visible_months=self.request.visible_months,
            required_months=self.request.required_months,
            scan_strategy=decision.scan_strategy,
            active_specialists=decision.specialists,
            region_purpose=decision.region_purpose,
            trigger_review_event_sequence=self.review_sequence,
            planner_decision_sha256=semantic_hash(decision),
        )
        self.selection = select(self.snapshot, self.request, self.plan.scan_strategy)
        self.executions.clear()
        self.canonical = None
        self.receipt_mismatch = False
        self.stage = "SCANNING"
        event = self.trace.emit(
            "PLAN_DECIDED",
            "orchestrator",
            {
                "decision": decision,
                "plan": self.plan,
                "previous_plan_sha256": previous.semantic_sha256 if previous else None,
            },
            iteration=version,
            plan_hash=self.plan.semantic_sha256,
            parent=self.review_sequence,
        )
        write_json(self.directory / f"plan-{version}.json", self.plan)
        self.trace.emit(
            "SELECTION_COMPLETED",
            "selector",
            {
                "strategy": self.selection.strategy,
                "selection_sha256": self.selection.selection_sha256,
                "scan_complete": self.selection.scan_complete,
                "missing_index_partitions": self.selection.missing_index_partitions,
                "selected_required_month_observations": len(self.selection.rows),
            },
            iteration=version,
            plan_hash=self.plan.semantic_sha256,
            parent=event,
        )
        if previous:
            self.trace.emit(
                "REFINEMENT_APPLIED",
                "controller",
                {
                    "before": previous,
                    "after": self.plan,
                    "criteria_hash_before": previous.canonical_query_sha256,
                    "criteria_hash_after": self.query_hash,
                    "strategy_changed": previous.scan_strategy != self.plan.scan_strategy,
                    "active_specialists_changed": set(previous.active_specialists)
                    != set(self.plan.active_specialists),
                    "refinements_used": version,
                },
                iteration=version,
                plan_hash=self.plan.semantic_sha256,
                parent=self.review_sequence,
            )

    def scan(self, decision: PriceDecision | SupplyDecision | RegionDecision) -> None:
        if self.selection is None or self.plan is None:
            self.abort("A trusted plan and selection are required before scans")
            return
        execution = dispatch(self.selection, self.plan, decision, self.run_id, self.directory / "tools")
        self.executions[decision.role] = execution
        self.trace.emit(
            "TOOL_COMPLETED",
            decision.role,
            {
                "tool": decision.tool,
                "tool_version": "1.0",
                "trusted_query_sha256": self.query_hash,
                "receipt": execution.receipt,
                "semantic_receipt_sha256": execution.receipt.semantic_sha256,
            },
            iteration=self.plan.version,
            plan_hash=self.plan.semantic_sha256,
        )
        if set(self.executions) == set(self.plan.active_specialists):
            try:
                self.canonical = aggregate(self.request, self.plan, tuple(self.executions.values()))
            except HousingError as error:
                if "RECEIPT_MISMATCH" not in error.message:
                    raise
                self.receipt_mismatch = True
                self.canonical = None
            self.stage = "REVIEW_REQUIRED"
            self.trace.emit(
                "AGGREGATE_COMPLETED",
                "aggregator",
                {
                    "canonical_sha256": semantic_hash(self.canonical) if self.canonical else None,
                    "provisional": not self.selection.scan_complete or self.receipt_mismatch,
                    "receipt_mismatch": self.receipt_mismatch,
                    "receipt_hashes": {k: v.receipt.semantic_sha256 for k, v in self.executions.items()},
                },
                iteration=self.plan.version,
                plan_hash=self.plan.semantic_sha256,
            )

    def signals(self) -> tuple[Signal, ...]:
        if self.receipt_mismatch:
            return ("RECEIPT_MISMATCH",)
        if self.canonical is None or self.selection is None:
            return ()
        sparse = any(m.listing_count < 5 for m in self.canonical.monthly)
        signals: list[Signal] = []
        if not self.selection.scan_complete:
            signals.append("INDEX_COVERAGE_MISMATCH")
        if sparse:
            signals.append("SPARSE_SLICE" if self.selection.strategy == "indexed" else "CONFIRMED_SPARSE")
        return tuple(signals) or ("COMPLETE_SUPPORT",)

    def apply_review(self, decision: ReviewDecision) -> None:
        signals = self.signals()
        if set(decision.signals) != set(signals):
            self.abort("Reviewer signals do not match the actual coverage evidence")
        if self.plan is None or self.selection is None:
            self.abort("Review requires a completed specialist pass")
            return
        if "RECEIPT_MISMATCH" in signals and self.plan.version > 0:
            if self.plan.version == 1 and "RECEIPT_MISMATCH" not in self.seen_review_signals:
                expected, action = "REFINE", "REBUILD_INDEX_AND_RESCAN"
            else:
                expected, action = "FAIL", None
        elif self.plan.scan_strategy == "indexed" and signals != ("COMPLETE_SUPPORT",):
            expected, action = "REFINE", "EXACT_RESCAN_WITH_REGION"
        elif not self.selection.scan_complete:
            expected, action = "FAIL", None
        else:
            expected, action = ("ACCEPT_LIMITED" if "CONFIRMED_SPARSE" in signals else "ACCEPT"), None
        if decision.decision != expected or decision.requested_action != action:
            self.abort("Reviewer action violates the evidence-based acceptance/refinement rule")
        self.seen_review_signals.update(decision.signals)
        self.review = decision
        self.review_sequence = self.trace.emit(
            "REVIEW_DECIDED",
            "reviewer",
            {"decision": decision, "evidence": self.context()},
            iteration=self.plan.version,
            plan_hash=self.plan.semantic_sha256,
        )
        if decision.decision == "FAIL":
            self.abort("Reviewer failed persistent integrity checks")
        self.stage = "PLAN_REQUIRED" if decision.decision == "REFINE" else "ACCEPTED"

    def facts(self) -> dict[str, str]:
        if self.canonical is None:
            return {}
        c = self.canonical
        facts = {
            "observations": f"{c.summary.total_observations} qualifying monthly observations from {c.window_start} through {c.window_end}.",
            "source": "Synthetic Dallas-themed test feed; these are generated observations.",
            "support": "Sparse monthly support confirmed by an authoritative scan."
            if "CONFIRMED_SPARSE" in self.signals()
            else "All twelve visible months have at least five qualifying observations.",
        }
        if c.summary.window_price_change_pct is not None:
            facts["first_to_last_price"] = (
                f"First-to-last median price change: {c.summary.window_price_change_pct}% across eleven monthly intervals."
            )
        if c.summary.last_month_price_yoy_pct is not None:
            facts["last_month_yoy"] = (
                f"Final-month median price year-over-year change: {c.summary.last_month_price_yoy_pct}%."
            )
        return facts

    def caveats(self) -> tuple[str, ...]:
        result = ["SYNTHETIC_DATA"]
        if "CONFIRMED_SPARSE" in self.signals():
            result.append("SPARSE_SUPPORT")
        if self.canonical and self.canonical.summary.total_observations == 0:
            result.append("NO_MATCHES")
        if self.selection and set(self.request.required_months) - set(self.selection.available_months):
            result.append("UNAVAILABLE_LOOKBACK")
        return tuple(result)

    def compose(self, decision: ReportDecision) -> None:
        facts = self.facts()
        if not set(decision.fact_ids).issubset(facts) or set(decision.caveat_codes) != set(self.caveats()):
            self.abort("Composer must select grounded facts and all applicable caveats")
        caveat_text = {
            "SYNTHETIC_DATA": "Synthetic Dallas-themed test feed; these are generated observations.",
            "SPARSE_SUPPORT": "Some visible months contain fewer than five qualifying observations.",
            "NO_MATCHES": "No observations matched the requested visible slice.",
            "UNAVAILABLE_LOOKBACK": "Some comparison months are outside the source snapshot.",
        }
        self.narrative = Narrative(
            fact_ids=decision.fact_ids,
            caveat_codes=decision.caveat_codes,
            text=" ".join(
                [
                    *(facts[key] for key in decision.fact_ids),
                    *(caveat_text[code] for code in decision.caveat_codes),
                ]
            ),
        )
        self.stage = "COMPOSED"
        write_json(
            self.directory / "composition.json",
            {"decision": decision, "fact_registry": facts, "narrative": self.narrative},
        )

    def planning_constraints(self) -> dict[str, object]:
        action = self.review.requested_action if self.review else "INITIAL"
        strategy = {
            "INITIAL": "indexed",
            "EXACT_RESCAN_WITH_REGION": "full_csv",
            "REBUILD_INDEX_AND_RESCAN": "rebuilt_index",
        }.get(action or "INITIAL")
        region = self.request.compare_regions or self.review is not None
        return {
            "required_action": action,
            "required_scan_strategy": strategy,
            "required_specialists": ("price", "supply", "region") if region else ("price", "supply"),
            "required_region_purpose": "public_comparison"
            if self.request.compare_regions
            else ("coverage_diagnostic" if region else "none"),
            "required_reason_codes": self.review.signals if self.review else (),
        }

    def context(self) -> dict[str, object]:
        return {
            "contract_version": "1.0",
            "schema_repair": self.repair_details,
            "stage": self.stage,
            "query": self.request.housing_query(self.snapshot.view_sha256),
            "query_sha256": self.query_hash,
            "iteration": self.plan.version if self.plan else 0,
            "plan": self.plan.model_dump(mode="json", exclude={"trigger_review_event_sequence"})
            if self.plan
            else None,
            "previous_review": self.review,
            "planning_constraints": self.planning_constraints() if self.stage == "PLAN_REQUIRED" else None,
            "previous_signals": tuple(sorted(self.seen_review_signals)),
            "signals": self.signals(),
            "monthly_counts": {m.month: m.listing_count for m in self.canonical.monthly}
            if self.canonical
            else {},
            "scan_complete": self.selection.scan_complete if self.selection else None,
            "receipt_hashes": {k: e.receipt.semantic_sha256 for k, e in sorted(self.executions.items())},
            "facts": self.facts() if self.stage in ("ACCEPTED", "COMPOSED", "FINALIZED") else {},
            "required_caveats": self.caveats() if self.stage in ("ACCEPTED", "COMPOSED", "FINALIZED") else (),
        }

    def finalize(self) -> dict[str, object]:
        if self.fatal:
            raise self.fatal
        if (
            self.stage != "COMPOSED"
            or self.canonical is None
            or self.narrative is None
            or self.selection is None
            or not self.selection.scan_complete
            or self.review is None
        ):
            self.abort("Only an accepted, composed, complete scan can be finalized")
            return {}
        sparse = tuple(m.month for m in self.canonical.monthly if m.listing_count < 5)
        self.output = AnalysisOutput(
            status="completed",
            canonical=self.canonical,
            presentation=present(self.canonical, self.request.display),
            quality=Quality(
                status="limited" if self.review.decision == "ACCEPT_LIMITED" else "complete",
                codes=self.caveats(),
                sparse_months=sparse,
            ),
            narrative=self.narrative,
            metadata=Metadata(
                run_id=self.run_id,
                dataset_id=self.request.dataset_id,
                snapshot_sha256=self.snapshot.source_sha256,
                dataset_view_sha256=self.snapshot.view_sha256,
                logical_multiset_sha256=self.snapshot.logical_multiset_sha256,
                query_sha256=self.query_hash,
                contract_version="1.0",
                mode=self.mode,
                model_profile=f"housing-qwen-v4-s{self.request.seed}",
                requested_seed=self.request.seed,
                effective_seed=self.request.seed if self.mode in ("live", "replay") else None,
                seed_support="verified_model_default"
                if self.mode == "live"
                else ("replay_recorded" if self.mode == "replay" else "unsupported"),
                prompt_bundle_sha256=self.prompt_hash,
                trace_path=str(self.trace.path.relative_to(ROOT))
                if self.trace.path.is_relative_to(ROOT)
                else str(self.trace.path),
                live_campaign_id=None,
            ),
        )
        self.stage = "FINALIZED"
        write_json(self.directory / "candidate-output.json", self.output)
        ack = {
            "status": "completed",
            "canonical_sha256": semantic_hash(self.canonical),
            "total_observations": self.canonical.summary.total_observations,
        }
        self.trace.emit(
            "AGENT_DECISION",
            "orchestrator",
            {
                "finalization_prepared": ack,
                "output_sha256": semantic_hash(self.output),
                "quality": self.output.quality,
                "composition_path": "composition.json",
            },
            iteration=self.plan.version if self.plan else 0,
            plan_hash=self.plan.semantic_sha256 if self.plan else None,
        )
        return ack
