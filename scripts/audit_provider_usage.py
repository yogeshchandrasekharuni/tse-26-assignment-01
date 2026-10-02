"""Write a report-side usage audit without modifying immutable campaign evidence."""

import argparse
from pathlib import Path

from housing.identity import ROOT, write_json
from housing.reporting.usage import campaign_usage

parser = argparse.ArgumentParser()
parser.add_argument("--campaign", default="artifacts/campaigns/headline-live-v1")
parser.add_argument("--output", type=Path, default=Path("reports/data/headline-provider-usage.json"))
args = parser.parse_args()
audit = campaign_usage(ROOT / args.campaign)
write_json(ROOT / args.output, audit)
print(
    f"Audited {audit['physical_runs']} physical live runs, {audit['recorded_responses']} responses; "
    f"{audit['reported_provider_attempts']} reported provider attempts. Output: {args.output}"
)
