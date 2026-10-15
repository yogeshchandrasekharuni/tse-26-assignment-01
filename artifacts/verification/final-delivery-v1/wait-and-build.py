"""Wait locally for the actual clean command, then build a PDF that still needs visual QA."""

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json

packet = Path(__file__).resolve().parent
completion = ROOT / "artifacts/verification/headline-clean-checkout-v3/process-result.json"
deadline = time.monotonic() + 3600
print("Local watcher: waiting for actual bounded-process full900 clean-checkout exit; no Codex/model calls.", flush=True)
while not completion.exists():
    if time.monotonic() >= deadline:
        raise TimeoutError("Clean checkout has not completed; no report/completion claim made")
    time.sleep(15)
result = json.loads(completion.read_bytes())
if result["exit_code"]:
    raise ValueError("Actual clean-checkout command failed; preserve its logs and investigate")
clean = json.loads((ROOT / "reports/data/clean-checkout.json").read_bytes())
assert clean["status"] == "verified" and clean["scope"] == "headline"
assert clean["logical_comparisons"] == 900
assert clean["revision"] == "8eb6727d7236f7bce14c97fdf9f5f86fddea1121"
assert all(command["exit_code"] == 0 for command in clean["commands"])
print("Actual clean checkout completed successfully; building the final evidence-bound PDF.", flush=True)
started = datetime.now(UTC).isoformat()
with (packet / "make-report.log").open("xb") as log:
    report = subprocess.run(["make", "report"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
write_json(
    packet / "report-build.json",
    {
        "status": "built_requires_all_page_visual_inspection" if report.returncode == 0 else "failed",
        "command": ["make", "report"],
        "exit_code": report.returncode,
        "started_at_utc": started,
        "ended_at_utc": datetime.now(UTC).isoformat(),
        "log_sha256": sha256_bytes((packet / "make-report.log").read_bytes()),
        "clean_checkout_sha256": sha256_bytes((ROOT / "reports/data/clean-checkout.json").read_bytes()),
        "interpretation": "A build is not visual QA, a submission-check pass or goal completion.",
    },
)
if report.returncode:
    raise ValueError("Final report build failed; preserve the actual log")
print("Final PDF built; all twelve rendered pages and submission checks remain required.", flush=True)
