"""Per-role exact scans; no canonical answer is computed without these results."""

from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from time import perf_counter_ns

from housing.contracts.decisions import PriceDecision, RegionDecision, SupplyDecision
from housing.contracts.errors import HousingError
from housing.contracts.stats import (
    CountMonth,
    ExactMonth,
    ExactZip,
    PartitionReceipt,
    PriceResult,
    Rational,
    RegionResult,
    StatsResult,
    SupplyResult,
    ToolExecution,
    ToolReceipt,
    WorkflowPlan,
)
from housing.data.models import Observation
from housing.data.store import Selection
from housing.identity import ROOT, semantic_hash, write_json
from housing.tools.exact import median

type ToolDecision = PriceDecision | SupplyDecision | RegionDecision


def rational(value: Fraction | None) -> Rational | None:
    return None if value is None else Rational.of(value)


def price_stats(selection: Selection, decision: PriceDecision) -> PriceResult:
    groups: dict[str, list[Observation]] = defaultdict(list)
    for row in selection.ordered_rows(decision.partition_order):
        groups[row.month].append(row)
    monthly: list[ExactMonth] = []
    for month in selection.request.required_months:
        available = month in selection.available_months
        rows = groups[month]
        monthly.append(
            ExactMonth(
                month=month,
                available=available,
                count=len(rows) if available else None,
                median_price_usd=rational(median(Fraction(r.price_cents, 100) for r in rows)),
                median_ppsf_usd=rational(median(Fraction(r.price_cents, 100 * r.sqft) for r in rows)),
            )
        )
    return PriceResult(tool="price_stats", monthly=tuple(monthly))


def supply_stats(selection: Selection, decision: SupplyDecision) -> SupplyResult:
    counts = Counter(row.month for row in selection.ordered_rows(decision.partition_order))
    return SupplyResult(
        tool="supply_stats",
        monthly=tuple(
            CountMonth(
                month=m,
                available=m in selection.available_months,
                count=counts[m] if m in selection.available_months else None,
            )
            for m in selection.request.required_months
        ),
    )


def region_stats(selection: Selection, decision: RegionDecision) -> RegionResult:
    groups: dict[str, list[Fraction]] = defaultdict(list)
    counts: Counter[str] = Counter()
    for row in selection.ordered_rows(decision.partition_order):
        counts[row.month] += 1
        if row.month in selection.request.visible_months:
            groups[row.zip].append(Fraction(row.price_cents, 100 * row.sqft))
    return RegionResult(
        tool="region_stats",
        purpose=decision.purpose,
        pooled=tuple(
            ExactZip(zip=z, count=len(groups[z]), median_ppsf_usd=rational(median(groups[z])))
            for z in selection.request.criteria.zips
        ),
        counts=tuple(
            CountMonth(
                month=m,
                available=m in selection.available_months,
                count=counts[m] if m in selection.available_months else None,
            )
            for m in selection.request.required_months
        ),
    )


def dispatch(
    selection: Selection,
    plan: WorkflowPlan,
    decision: ToolDecision,
    run_id: str,
    artifact_dir: Path,
) -> ToolExecution:
    """All handles are bound by the application; the model supplies only the allowed intent."""
    started = perf_counter_ns()
    if (
        plan.canonical_query_sha256 != selection.query_sha256
        or plan.dataset_view_sha256 != selection.snapshot.view_sha256
        or plan.scan_strategy != selection.strategy
        or plan.required_months != selection.request.required_months
        or plan.visible_months != selection.request.visible_months
    ):
        raise HousingError(
            "AGENT_POLICY_ERROR", "Plan does not bind this immutable selection", "tool_dispatch"
        )
    if decision.role not in plan.active_specialists:
        raise HousingError("AGENT_POLICY_ERROR", "Inactive specialist attempted a tool", "tool_dispatch")
    result: StatsResult
    if isinstance(decision, PriceDecision):
        result = price_stats(selection, decision)
    elif isinstance(decision, SupplyDecision):
        result = supply_stats(selection, decision)
    elif isinstance(decision, RegionDecision):
        if decision.purpose != plan.region_purpose:
            raise HousingError("AGENT_POLICY_ERROR", "Region purpose differs from its plan", "tool_dispatch")
        result = region_stats(selection, decision)
    else:
        raise HousingError("AGENT_POLICY_ERROR", "Unknown tool intent", "tool_dispatch")
    ids: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in selection.rows:
        ids[row.month, row.zip].append(row.record_id)
    keys = [(m, z) for m in selection.request.required_months for z in selection.request.criteria.zips]
    keys.sort(key=(lambda k: k) if decision.partition_order == "month_asc" else lambda k: (k[1], k[0]))
    partitions = tuple(
        PartitionReceipt(
            month=m,
            zip=z,
            available=m in selection.available_months,
            index_present=selection.strategy != "indexed" or (m, z) in selection.snapshot.index,
            selected_count=len(ids[m, z]) if m in selection.available_months else None,
            selected_record_ids_sha256=semantic_hash(sorted(ids[m, z])),
            execution_order=decision.partition_order,
        )
        for m, z in keys
    )
    prefix = artifact_dir / f"iteration-{plan.version}" / decision.tool
    result_path = prefix.with_suffix(".result.json")
    partitions_path = prefix.with_suffix(".partitions.json")
    write_json(result_path, result)
    write_json(partitions_path, partitions)
    receipt = ToolReceipt(
        schema_version="1.0",
        receipt_id=f"{run_id}.{plan.version}.{decision.tool}",
        tool=decision.tool,
        tool_version="1.0",
        run_id=run_id,
        iteration=plan.version,
        plan_sha256=plan.semantic_sha256,
        canonical_query_sha256=selection.query_sha256,
        dataset_view_sha256=selection.snapshot.view_sha256,
        selection_sha256=selection.selection_sha256,
        strategy=selection.strategy,
        source_snapshot_complete=True,
        scan_complete=selection.scan_complete,
        visible_months=selection.request.visible_months,
        unavailable_lookback_months=tuple(
            m for m in selection.request.required_months if m not in selection.available_months
        ),
        partition_receipts_path=str(partitions_path.relative_to(ROOT))
        if partitions_path.is_relative_to(ROOT)
        else str(partitions_path),
        result_path=str(result_path.relative_to(ROOT))
        if result_path.is_relative_to(ROOT)
        else str(result_path),
        result_sha256=semantic_hash(result),
        decision_sha256=semantic_hash(decision),
        duration_ms=(perf_counter_ns() - started) // 1_000_000,
    )
    write_json(prefix.with_suffix(".receipt.json"), receipt)
    return ToolExecution(receipt=receipt, result=result)
