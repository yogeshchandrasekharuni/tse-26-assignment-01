"""Bind the reviewed representatives to concise, honestly scoped report prose."""

import json
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json

PACKET = Path(__file__).resolve().parent
review = json.loads((PACKET / "review.json").read_bytes())
assert review["status"] == "verified_fixed_top_three_representatives"
assert review["ranked_relations"][:3] == ["MR03", "MR05", "MR07"]
hashes = dict(review["source_hashes"])
for relative, digest in hashes.items():
    assert sha256_bytes((ROOT / relative).read_bytes()) == digest, relative
for path in [
    Path(__file__),
    PACKET / "review.json",
    PACKET / "check.log",
    *sorted(PACKET.glob("*-boundary.json")),
    *sorted((PACKET / "minimal-captures").rglob("*")),
]:
    if path.is_file():
        hashes[str(path.relative_to(ROOT))] = sha256_bytes(path.read_bytes())

other_mechanisms = [
    ROOT / "artifacts/rca/MR01-b013-s104729/diagnosis.md",
    ROOT / "artifacts/rca/MR01-b013-s104729/boundary-diagnostic.json",
    ROOT / "artifacts/rca/MR01-b013-s104729/20261003T020129Z/comparison.json",
    ROOT / "artifacts/rca/MR05-b020-s130363/diagnosis.md",
    ROOT / "artifacts/rca/MR05-b020-s130363/boundary-diagnostic.json",
    ROOT / "artifacts/rca/MR05-b020-s130363/20261007T061629Z/comparison.json",
]
for path in other_mechanisms:
    hashes[str(path.relative_to(ROOT))] = sha256_bytes(path.read_bytes())

write_json(
    ROOT / "reports/data/diagnosis.json",
    {
        "schema_version": "reviewed-headline-diagnosis-1",
        "status": "verified",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "campaign_id": review["campaign_id"],
        "headline_sha256": review["headline_sha256"],
        "ranked_relations": review["ranked_relations"],
        "selection_rule": "Descending exact base-any-seed rate, descending violating bases, ascending MR identifier; first lexicographic violating case per selected MR",
        "summary": "All 690 numerically comparable pairs satisfy their projections; 210 pairs fail output contracts. The top three relations share one demonstrated representative mechanism: parent purpose leakage followed by a queued-role/pending-repair conflict. These are three ranked relations, not three independent bugs or evidence of transformation causality.",
        "report_blocks": [
            [
                "MR03: replicated observations - 16/30 bases",
                "b001/104729 follow-up: raw checks prove 34,560 to 69,120 unique-record rows and 2,880 to 5,760 selected observations. The parent sends public_comparison to Price, whose schema requires statistics. Price fails; Supply returns valid JSON while Price repair is pending. The controller stops before numeric tools. The source reuses MR01's successful capture.",
            ],
            [
                "MR05: wider price band - 15/30 bases",
                "b001/104729 source fails through the same four-decision path. Independent inclusive predicates prove 2,149 source observations and a proper 2,880-observation superset after widening. Crucially, the failure precedes the transformation. It supports a coordination/contract diagnosis, not a counterexample to count monotonicity or a claim that widening caused failure.",
            ],
            [
                "MR07: shifted window - 14/30 bases",
                "b001/130363 follow-up repeats the mechanism. All eleven overlap months have identical raw multisets; 240 records leave and 240 enter. Its source is reused from MR01. MR07 wins its tie with MR08/MR09 by identifier; overlapping intervals and shared sources prevent an isolated-sensitivity interpretation.",
            ],
            [
                "Reduction, alternatives and prospective correction",
                "Each failure replays from only a manifest, terminal and four cassettes: four decisions, zero network, no saved tools or output. Dataset/semantic identities remain fixed. Valid witnesses exclude the proposed data/relation explanations for these boundaries. Other reviewed natural failures include Reviewer schema echo and Composer caveat omission. Role-specific purpose hints and queue-aware repair are proposed future fixes, not evaluated improvements.",
            ],
        ],
        "selected": review["selected"],
        "causal_scope": review["interpretation"],
        "reduction_scope": "Only persisted replay dependencies were reduced. Exact semantic identities, complete frozen datasets and four original model responses remain; no smallest statistical input or new model sample is claimed.",
        "alternative_explanations": {
            "agent_or_aggregation": "Parent delegates a Region-only purpose to Price; Price copies it and fails its role schema. A pending Price repair then causes the controller to reject an actually generated valid Supply reply. No aggregation executes in these three runs.",
            "data_artifact": "Independent raw checks confirm valid record identities and meaningful transformations. The first divergence is a role-purpose literal, not a data arithmetic contradiction.",
            "bad_relation": "Exact twofold multiset replication, proper price-band inclusion and identical eleven-month overlap witnesses hold. No complete numeric pair contradicts those projections.",
            "harness_fault": "Actual case/seed/leg and successful-source lineage are bound; current service reproduces the same boundary with source outputs and receipts absent. The eligible output-contract outcome follows the declared protocol. This does not prove every possible harness behavior correct.",
        },
        "mitigation_status": "Proposed only. Preserve this corpus. Any changed prompt, coordination policy or model requires a new version/campaign; no all-pass claim or additional live experiment is made.",
        "supporting_artifact_hashes": hashes,
    },
)
print("Reviewed diagnosis bound to raw evidence and three actual four-decision minimal-dependency replays.")
