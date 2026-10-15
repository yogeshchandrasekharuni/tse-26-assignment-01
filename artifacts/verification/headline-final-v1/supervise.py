"""Wait locally for the original campaign, then run read-only closure audits once."""

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json

packet = Path(__file__).resolve().parent
campaign = ROOT / "artifacts/campaigns/headline-live-v1"
original_pid = int(sys.argv[1])
required = ("finished.json", "headline.json", "runtime.json", "artifact_hashes.json", "cases.jsonl")
deadline = time.monotonic() + 3 * 60 * 60
print(
    f"Local closure job started at {datetime.now(UTC).isoformat()}; original PID {original_pid}", flush=True
)
while True:
    try:
        ready = all((campaign / name).is_file() for name in required)
        if ready:
            json.loads((campaign / "artifact_hashes.json").read_bytes())
            break
    except json.JSONDecodeError:
        pass  # A last file can briefly be visible while its writer is finishing.
    try:
        os.kill(original_pid, 0)
    except ProcessLookupError:
        raise SystemExit(
            "Original campaign process is missing before complete closure; inspect its retained output"
        )
    except PermissionError:
        pass  # Permission is not proof that the original process stopped.
    if time.monotonic() >= deadline:
        raise SystemExit(
            "Local watcher timeout only; inspect original process, never restart from this timeout"
        )
    time.sleep(30)

commands = [
    ([sys.executable, str(packet / "check.py")], packet / "check.log"),
    (
        [
            sys.executable,
            "artifacts/observability/plan-aware-preflight-v1/check.py",
            "--output",
            "complete.json",
        ],
        ROOT / "artifacts/observability/plan-aware-preflight-v1/complete-check.log",
    ),
]
records = []
for command, log in commands:
    print(f"Running local closure audit: {command[1]}", flush=True)
    with log.open("xb") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False)
    records.append(
        {
            "command": command,
            "exit_code": result.returncode,
            "log": str(log.relative_to(ROOT)),
            "log_sha256": sha256_bytes(log.read_bytes()),
        }
    )
    write_json(
        packet / "closure-job.json",
        {
            "scope": "Local read-only capture and projection audits; not assignment completion",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "commands": records,
        },
    )
    if result.returncode:
        raise SystemExit(f"Read-only closure audit failed; preserved {log.relative_to(ROOT)}")
print(
    "Both closure audits completed successfully; reviewed diagnosis, full playback and dashboard work remain.",
    flush=True,
)
