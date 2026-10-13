"""Local-only completion watcher; no model, network, Git, or Codex calls."""

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
CAMPAIGN = ROOT / "artifacts/campaigns/headline-live-v1"


def record(event: str, **details: object) -> None:
    print(json.dumps({"at_utc": datetime.now(UTC).isoformat(), "event": event, **details}), flush=True)


def command(script: str, log: Path) -> int:
    with log.open("xb") as stream:
        result = subprocess.run([sys.executable, script], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False)
    record("offline_command_finished", script=script, exit_code=result.returncode, log=str(log.relative_to(ROOT)))
    return result.returncode


def main() -> None:
    record("watch_started", scope="Observe existing campaign; assignment remains unfinished", interval_seconds=60)
    deadline = time.monotonic() + 12 * 60 * 60
    last = None
    checked_mr05 = False
    while time.monotonic() < deadline:
        try:
            progress = json.loads((CAMPAIGN / "progress.json").read_bytes())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(60)
            continue
        if progress != last:
            record("campaign_progress", **progress)
            last = progress
        checkpoint = ROOT / "artifacts/verification/mr05-live-checkpoint-v1"
        if not checked_mr05 and len(list((CAMPAIGN / "cases").glob("MR05-*/result.json"))) == 90:
            checked_mr05 = True
            if not (checkpoint / "checkpoint.json").exists():
                command(str((checkpoint / "check.py").relative_to(ROOT)), checkpoint / "check.log")
        required = ("finished.json", "headline.json", "runtime.json", "artifact_hashes.json", "cases.jsonl")
        if progress["completed_comparisons"] == 900 and all((CAMPAIGN / name).is_file() for name in required):
            headline = json.loads((CAMPAIGN / "headline.json").read_bytes())
            complete = len(headline) == 10 and all(row["complete"] for row in headline)
            if complete:
                if not (ROOT / "reports/data/headline-provider-usage.json").exists():
                    command("scripts/audit_provider_usage.py", PACKET / "provider-usage.log")
                if not (ROOT / "reports/data/headline-live-v1-diagnosis-candidates.json").exists():
                    command("scripts/prepare_diagnosis.py", PACKET / "diagnosis-candidates.log")
            ready = {"status": "ready_for_codex_review", "at_utc": datetime.now(UTC).isoformat(), "logical_comparisons": 900, "headline_complete": complete, "assignment_complete": False, "remaining": ["Full clean-checkout playback", "Reviewed diagnosis", "Current Langfuse delivery/browser proof", "Final UI/PDF QA and submission checks"]}
            (PACKET / "ready.json").write_text(json.dumps(ready, indent=2) + "\n")
            record("artifacts_ready", **ready)
            return
        time.sleep(60)
    record("watch_timeout", assignment_complete=False, note="Inspect the original process before taking action; never restart from this timeout alone")


if __name__ == "__main__":
    main()
