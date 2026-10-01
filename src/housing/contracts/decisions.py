from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from housing.contracts.common import (
    Action,
    FrozenModel,
    PartitionOrder,
    RegionPurpose,
    Signal,
    Specialist,
    Strategy,
    array_to_tuple,
)


class PlanDecision(FrozenModel):
    role: Literal["orchestrator"]
    decision_type: Literal["plan"]
    action: Action
    scan_strategy: Strategy
    specialists: Annotated[tuple[Specialist, ...], Field(min_length=2, max_length=3)]
    region_purpose: RegionPurpose
    reason_codes: tuple[Signal, ...]

    _sets = field_validator("specialists", "reason_codes", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def required_specialists(self) -> PlanDecision:
        if len(set(self.specialists)) != len(self.specialists) or len(set(self.reason_codes)) != len(
            self.reason_codes
        ):
            raise ValueError("Plan arrays must contain unique entries")
        if not {"price", "supply"}.issubset(self.specialists):
            raise ValueError("Price and Supply are mandatory")
        if ("region" in self.specialists) != (self.region_purpose != "none"):
            raise ValueError("Region activation and purpose must agree")
        expected = {
            "INITIAL": "indexed",
            "EXACT_RESCAN_WITH_REGION": "full_csv",
            "REBUILD_INDEX_AND_RESCAN": "rebuilt_index",
        }
        if self.scan_strategy != expected[self.action]:
            raise ValueError("Plan action and scan strategy disagree")
        if self.action != "INITIAL" and "region" not in self.specialists:
            raise ValueError("Refinement must activate Region diagnosis")
        return self


class PriceDecision(FrozenModel):
    role: Literal["price"]
    decision_type: Literal["tool_intent"]
    tool: Literal["price_stats"]
    partition_order: PartitionOrder
    purpose: Literal["statistics"]


class SupplyDecision(FrozenModel):
    role: Literal["supply"]
    decision_type: Literal["tool_intent"]
    tool: Literal["supply_stats"]
    partition_order: PartitionOrder
    purpose: Literal["statistics"]


class RegionDecision(FrozenModel):
    role: Literal["region"]
    decision_type: Literal["tool_intent"]
    tool: Literal["region_stats"]
    partition_order: PartitionOrder
    purpose: Literal["public_comparison", "coverage_diagnostic"]


class ReviewDecision(FrozenModel):
    role: Literal["reviewer"]
    decision_type: Literal["review"]
    decision: Literal["ACCEPT", "REFINE", "ACCEPT_LIMITED", "FAIL"]
    signals: Annotated[tuple[Signal, ...], Field(min_length=1)]
    requested_action: Literal["EXACT_RESCAN_WITH_REGION", "REBUILD_INDEX_AND_RESCAN"] | None

    _signals = field_validator("signals", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def refinement_has_action(self) -> ReviewDecision:
        if len(set(self.signals)) != len(self.signals):
            raise ValueError("Review signals must be unique")
        if (self.decision == "REFINE") != (self.requested_action is not None):
            raise ValueError("Only REFINE can and must request an action")
        return self


class ReportDecision(FrozenModel):
    role: Literal["composer"]
    decision_type: Literal["report"]
    fact_ids: Annotated[tuple[str, ...], Field(min_length=1, max_length=8)]
    caveat_codes: tuple[
        Literal["SYNTHETIC_DATA", "SPARSE_SUPPORT", "NO_MATCHES", "UNAVAILABLE_LOOKBACK"], ...
    ]

    _arrays = field_validator("fact_ids", "caveat_codes", mode="before")(array_to_tuple)

    @model_validator(mode="after")
    def unique_facts_and_caveats(self) -> ReportDecision:
        if not all(self.fact_ids) or len(set(self.fact_ids)) != len(self.fact_ids):
            raise ValueError("Fact IDs must be nonempty and unique")
        if len(set(self.caveat_codes)) != len(self.caveat_codes):
            raise ValueError("Caveat codes must be unique")
        return self


class FinalizeDecision(FrozenModel):
    role: Literal["orchestrator"]
    decision_type: Literal["finalize"]
    action: Literal["return_verified_report"]


type RoleDecision = Annotated[
    PlanDecision | PriceDecision | SupplyDecision | RegionDecision | ReviewDecision | ReportDecision,
    Field(discriminator="role"),
]
# Pydantic resolves PEP 695 aliases at runtime; mypy's TypeAdapter stub does not model TypeAliasType.
ROLE_DECISION: TypeAdapter[RoleDecision] = TypeAdapter(RoleDecision)  # type: ignore[arg-type]
