"""Small real tools for the framework spike, deliberately separate from production."""

import csv
from fractions import Fraction
from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict

from probe_support import Evidence, digest


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    role: Literal["reviewer"]
    decision: Literal["ACCEPT", "REFINE", "ACCEPT_LIMITED", "FAIL"]
    requested_action: Literal["EXACT_RESCAN_WITH_REGION"] | None


class ProbeQuery(TypedDict):
    window_start: str
    window_end: str
    zips: list[str]
    property_types: list[str]
    bedrooms: list[int]
    price_bounds: list[int | None]


def median(values: list[Fraction]) -> Fraction | None:
    ordered = sorted(values)
    n = len(ordered)
    return None if not n else ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


class ProbeTools:
    """Controller binds all fixture/query/selection arguments; models cannot broaden them."""

    def __init__(self, evidence: Evidence):
        self.evidence = evidence
        with Path("housing-tse-codex-handoff/fixtures/low_support.csv").open() as f:
            self.rows = list(csv.DictReader(f))
        self.query: ProbeQuery = {"window_start": "2025-10", "window_end": "2026-09", "zips": ["75204"],
                      "property_types": ["condo"], "bedrooms": [2, 2], "price_bounds": [None, None]}
        self.query_hash = digest(self.query)
        self.strategy = "indexed"
        self.active = ["price", "supply"]
        self.refinements = 0
        self.receipts: dict[str, dict] = {}
        self.reviews: list[dict] = []
        self.plans = [{"strategy": self.strategy, "active": self.active.copy()}]
        self.accepted = False
        self.report: dict | None = None

    def selected(self) -> list[dict[str, str]]:
        return [r for r in self.rows if self.query["window_start"] <= r["month"] <= self.query["window_end"]
                and not (self.strategy == "indexed" and r["month"] == "2026-03")]

    def receipt(self, role: str, result: dict) -> dict:
        rows = self.selected()
        body = {"role": role, "strategy": self.strategy, "query_sha256": self.query_hash,
                "selection_sha256": digest(sorted(r["record_id"] for r in rows)),
                "selected_observations": len(rows), "result": result}
        body["receipt_sha256"] = digest(body)
        self.receipts[role] = body
        self.evidence.log("TOOL_COMPLETED", **body)
        return body

    def scan_price(self) -> dict:
        """Run the exact price scan for the controller-bound current plan. Call once for this task."""
        rows = self.selected()
        values = [Fraction(int(r["price_cents"]), 100) for r in rows]
        value = median(values)
        return self.receipt("price", {"pooled_median_usd_rational": str(value) if value else None})

    def scan_supply(self) -> dict:
        """Count the current exact selection and check the index against the authoritative fixture."""
        rows = self.selected()
        months = sorted({r["month"] for r in self.rows if r["month"] >= "2025-10"})
        counts = {m: sum(r["month"] == m for r in rows) for m in months}
        return self.receipt("supply", {"monthly_counts": counts,
                                       "scan_complete": self.strategy == "full_csv",
                                       "source_snapshot_complete": True})

    def scan_region(self) -> dict:
        """Diagnose the requested ZIP only; available after REFINE activates Region. Never change criteria."""
        if self.strategy != "full_csv" or "region" not in self.active:
            raise ValueError("AGENT_POLICY_ERROR: Region not activated")
        return self.receipt("region", {"requested_zips": ["75204"], "support": "sparse_confirmed"})

    def inspect_coverage(self) -> dict:
        """Inspect current Price/Supply receipts before choosing a review decision. Do not infer evidence."""
        if not {"price", "supply"}.issubset(self.receipts):
            raise ValueError("AGENT_POLICY_ERROR: both specialist receipts required first")
        if self.receipts["price"]["selection_sha256"] != self.receipts["supply"]["selection_sha256"]:
            raise ValueError("RECEIPT_MISMATCH")
        if self.strategy == "full_csv" and "region" not in self.receipts:
            raise ValueError("AGENT_POLICY_ERROR: Region diagnosis required before accepting")
        result = {"strategy": self.strategy, "refinements": self.refinements,
                  "scan_complete": self.strategy == "full_csv", "source_snapshot_complete": True,
                  "signals": ["INDEX_COVERAGE_MISMATCH", "SPARSE_SLICE"] if self.strategy == "indexed"
                             else ["CONFIRMED_SPARSE"],
                  "total_observations": self.receipts["supply"]["selected_observations"],
                  "receipt_sha256": {k: v["receipt_sha256"] for k, v in sorted(self.receipts.items())}}
        self.evidence.log("COVERAGE_INSPECTED", **result)
        return result

    def submit_review(self, decision: Literal["REFINE", "ACCEPT_LIMITED"],
                      requested_action: Literal["EXACT_RESCAN_WITH_REGION"] | None = None) -> dict:
        """Submit your review: indexed mismatch needs REFINE plus EXACT_RESCAN_WITH_REGION;
        authoritative confirmed sparsity needs ACCEPT_LIMITED plus null. Returns the accepted decision."""
        evidence = self.inspect_coverage()
        review = ReviewDecision(role="reviewer", decision=decision, requested_action=requested_action)
        if self.strategy == "indexed":
            if review.decision != "REFINE" or review.requested_action != "EXACT_RESCAN_WITH_REGION":
                raise ValueError("AGENT_POLICY_ERROR: mismatch cannot be accepted")
            self.strategy = "full_csv"
            self.active = ["price", "supply", "region"]
            self.refinements += 1
            plan = {"strategy": self.strategy, "active": self.active.copy()}
            assert plan not in self.plans and self.refinements <= 2
            self.plans.append(plan)
            self.receipts.clear()
            self.evidence.log("REFINEMENT_APPLIED", before=self.plans[-2], after=plan,
                              criteria_hash_before=self.query_hash, criteria_hash_after=digest(self.query),
                              trigger=review.model_dump())
        else:
            if review.decision != "ACCEPT_LIMITED" or review.requested_action is not None:
                raise ValueError("AGENT_POLICY_ERROR: authoritative sparse scan must stop as limited")
            self.accepted = True
        self.reviews.append(review.model_dump())
        self.evidence.log("REVIEW_DECIDED", decision=review.model_dump(), input_evidence=evidence)
        return {"review": review.model_dump(), "next_strategy": self.strategy,
                "active_specialists": self.active, "query_sha256": self.query_hash}

    def compose_report(self, fact_ids: list[Literal["observations", "support"]]) -> dict:
        """Select both supported facts after acceptance. Render the report from tool receipts, without invented values."""
        if not self.accepted:
            raise ValueError("AGENT_POLICY_ERROR: cannot compose before acceptance")
        if set(fact_ids) != {"observations", "support"}:
            raise ValueError("AGENT_POLICY_ERROR: select observations and support facts")
        count = self.receipts["supply"]["selected_observations"]
        self.report = {"source_kind": "synthetic_probe_fixture", "injection": "index_omission",
                       "total_observations": count, "quality": "limited", "fact_ids": fact_ids,
                       "text": f"Synthetic probe fixture: {count} observations; sparse support confirmed."}
        self.evidence.log("COMPOSED", report=self.report)
        return self.report
