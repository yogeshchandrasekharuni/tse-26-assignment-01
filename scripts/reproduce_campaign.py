"""Verify immutable evidence, then recompute a whole live campaign offline."""

import argparse
import asyncio
import json
from datetime import UTC, datetime

from housing.evaluation.aggregate import aggregate
from housing.evaluation.runner import CampaignRunner
from housing.identity import ROOT, sha256_bytes

parser = argparse.ArgumentParser()
parser.add_argument("--reference", default="artifacts/campaigns/headline-live-v1")
parser.add_argument("--pilot", action="store_true")
args = parser.parse_args()
reference = (ROOT / args.reference).resolve()
if not reference.is_relative_to(ROOT / "artifacts/campaigns"):
    raise SystemExit("Reference must be a local registered campaign")
manifest = json.loads((reference / "manifest.json").read_bytes())
headlines = json.loads((reference / "headline.json").read_bytes())
expected = 9 if args.pilot else 900
if (
    manifest["mode"] != "live"
    or manifest["expected_comparisons"] != expected
    or not all(row["complete"] for row in headlines)
):
    raise SystemExit("Live reference is incomplete or has the wrong campaign scope")
hashes = json.loads((reference / "artifact_hashes.json").read_bytes())
for name, expected_hash in hashes.items():
    path = (reference / name).resolve()
    if (
        not path.is_relative_to(reference)
        or not path.is_file()
        or sha256_bytes(path.read_bytes()) != expected_hash
    ):
        raise SystemExit(f"Live artifact integrity rejected: {name}")
destination = ROOT / "artifacts/reproductions" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
runner = CampaignRunner(destination, ROOT / manifest["cohort_path"], mode="replay", live_reference=reference)
asyncio.run(runner.run())
aggregate(destination, minimum_bases=3 if args.pilot else 30)
print(f"Matched {expected} recomputed comparisons. Evidence: {destination.relative_to(ROOT)}")
