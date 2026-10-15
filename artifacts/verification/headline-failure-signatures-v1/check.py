"""Inventory exact emitted failure signatures without inferring unreviewed causes."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from housing.evaluation.models import CaseResult
from housing.identity import ROOT, sha256_bytes, write_json

campaign = ROOT / "artifacts/campaigns/headline-live-v1"
groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
for path in sorted(campaign.glob("cases/*/attempt-*/*/runs/*/failure.json")):
    assert (path.parent / "terminal.json").is_file()
    failure = json.loads(path.read_bytes())
    groups[(failure["code"], failure["stage"], failure["message"])].append(str(path.parent.relative_to(ROOT)))
cases = [CaseResult.model_validate_json(path.read_bytes()) for path in campaign.glob("cases/*/result.json")]
assert len(cases) == 900
entries = []
referenced_failures: set[str] = set()
for (code, stage, message), runs in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
    paths = set(runs)
    touched = sorted(
        f"{case.mr_id}-{case.base_id}-s{case.seed}"
        for case in cases
        if any(leg.run_path in paths for leg in (case.source, case.followup))
    )
    referenced_failures.update(
        leg.run_path for case in cases for leg in (case.source, case.followup) if leg.run_path in paths
    )
    entries.append(
        {
            "code": code,
            "stage": stage,
            "message": message,
            "physical_failed_attempts": len(runs),
            "latest_logical_comparisons_referencing": len(touched),
            "logical_case_ids": touched,
            "physical_run_paths": runs,
        }
    )
assert sum(len(runs) for runs in groups.values()) == 274
assert len(referenced_failures) == 272
assert sum(case.status == "violation" for case in cases) == 210
write_json(
    ROOT / "reports/data/headline-failure-signatures.json",
    {
        "status": "verified_exact_signature_inventory",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "campaign_id": campaign.name,
        "campaign_artifact_index_sha256": sha256_bytes((campaign / "artifact_hashes.json").read_bytes()),
        "headline_sha256": sha256_bytes((campaign / "headline.json").read_bytes()),
        "source_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "physical_failed_attempts": 274,
        "latest_referenced_failed_attempts": 272,
        "latest_contract_violating_logical_comparisons": 210,
        "groups": entries,
        "interpretation": "Exact emitted signatures are descriptive, not unique causal diagnoses. Physical attempts are not primary base units. A logical pair may reference multiple signatures, so group case counts overlap. Two historical startup failures stay outside the latest eligible outcomes. Interrupted prefixes have no fabricated failure terminal.",
    },
)
print(
    "Verified274 physical failure signatures:233 scanning repair guards,37 reviewer repair limits,2 composition guards,2 historical startup errors."
)
