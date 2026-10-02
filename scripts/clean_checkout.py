"""Exercise a detached committed checkout offline; preserve logs and full recomputed evidence."""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from housing.identity import ROOT, sha256_bytes, write_json


def main() -> None:
    reference = ROOT / "artifacts/campaigns/headline-live-v1"
    if not (reference / "headline.json").is_file() or not all(
        row["complete"] for row in json.loads((reference / "headline.json").read_bytes())
    ):
        raise SystemExit("Clean-checkout verification requires a complete committed headline campaign")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "artifacts/verification" / f"clean-{stamp}"
    evidence.mkdir(parents=True, exist_ok=False)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    checkout = Path(tempfile.mkdtemp(prefix="housing-clean-")) / "repository"
    subprocess.run(["git", "worktree", "add", "--detach", str(checkout), revision], cwd=ROOT, check=True)
    initial_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout, text=True)
    if initial_status:
        raise ValueError("Detached checkout was not initially clean")
    committed_headline = checkout / "artifacts/campaigns/headline-live-v1/headline.json"
    if (
        not committed_headline.is_file()
        or committed_headline.read_bytes() != (reference / "headline.json").read_bytes()
    ):
        raise ValueError("Headline evidence has not been committed at the tested revision")
    environment = dict(os.environ)
    environment.update(
        {
            "UV_OFFLINE": "1",
            "npm_config_offline": "true",
            "PYTHONHASHSEED": "0",
            "UV_CACHE_DIR": str(ROOT / ".cache/uv"),
            "UV_PYTHON_INSTALL_DIR": str(ROOT / ".python"),
        }
    )
    # Reuse the verified installer, never an unpinned network bootstrap. Both package managers are offline.
    installer = ROOT / ".cache/uv-bootstrap/bin/uv"
    commands = [
        ["make", "setup", f"UV={installer}"],
        ["make", "data"],
        ["make", "check"],
        ["make", "probe-replay"],
        ["make", "reproduce"],
    ]
    records = []
    try:
        for index, command in enumerate(commands, 1):
            log = evidence / f"{index:02}-{command[1]}.log"
            started = datetime.now(UTC).isoformat()
            print(f"Clean checkout: {' '.join(command[:2])}", flush=True)
            with log.open("wb") as stream:
                result = subprocess.run(
                    command,
                    cwd=checkout,
                    env=environment,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            records.append(
                {
                    "command": command,
                    "started_at_utc": started,
                    "ended_at_utc": datetime.now(UTC).isoformat(),
                    "exit_code": result.returncode,
                    "log": str(log.relative_to(ROOT)),
                    "log_sha256": sha256_bytes(log.read_bytes()),
                }
            )
            if result.returncode:
                raise ValueError(f"Clean-checkout command failed; preserved log: {log.relative_to(ROOT)}")
        reproduced = []
        for path in sorted((checkout / "artifacts/reproductions").glob("*/reproduction-comparison.json")):
            item = json.loads(path.read_bytes())
            if item["logical_comparisons"] == 900 and item["status"] == "matched":
                # Only copy a newly created directory, never overwrite committed evidence.
                target = ROOT / path.parent.relative_to(checkout)
                if not target.exists():
                    shutil.copytree(path.parent, target)
                    reproduced.append(str(target.relative_to(ROOT)))
        if not reproduced:
            raise ValueError("No new complete offline reproduction was produced")
        packet = {
            "status": "verified",
            "revision": revision,
            "initial_git_status": initial_status,
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "commands": records,
            "network_policy": "uv and npm offline; production playback blocks socket connections",
            "bootstrap": "Previously completed setup supplies package caches and pinned Python; no model server required",
            "reproductions": reproduced,
            "headline_sha256": sha256_bytes(committed_headline.read_bytes()),
        }
        write_json(evidence / "result.json", packet)
        write_json(ROOT / "reports/data/clean-checkout.json", packet)
        subprocess.run(["git", "worktree", "remove", "--force", str(checkout)], cwd=ROOT, check=True)
        checkout.parent.rmdir()
        print(
            f"Verified committed clean checkout {revision}; {len(reproduced)} full offline reproduction(s)."
        )
    except Exception:
        write_json(
            evidence / "failed.json",
            {
                "status": "failed",
                "revision": revision,
                "checkout_preserved": str(checkout),
                "commands": records,
            },
        )
        raise


if __name__ == "__main__":
    main()
