"""Exercise the real completed live entrypoint and prove capture bytes/mtimes stay fixed."""

import contextlib
import io
import json
import runpy
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json

packet = Path(__file__).resolve().parent
campaign = ROOT / "artifacts/campaigns/headline-live-v1"


def inventory() -> dict[str, tuple[int, int, str]]:
    result = {}
    for path in sorted(campaign.rglob("*")):
        if path.is_file():
            stat = path.stat()
            result[str(path.relative_to(campaign))] = (
                stat.st_size,
                stat.st_mtime_ns,
                sha256_bytes(path.read_bytes()),
            )
    return result


before = inventory()
with (packet / "make-evaluate-live.log").open("xb") as stream:
    completed = subprocess.run(
        ["make", "evaluate-live"], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False
    )
assert completed.returncode == 0
attempts: list[str] = []


def forbidden(*args: object, **kwargs: object) -> None:
    attempts.append("forbidden network or subprocess fallback")
    raise AssertionError("Completed capture entrypoint attempted new work")


stdout = io.StringIO()
with (
    patch.object(socket.socket, "connect", forbidden),
    patch.object(socket.socket, "connect_ex", forbidden),
    patch.object(socket, "create_connection", forbidden),
    patch.object(socket, "getaddrinfo", forbidden),
    patch.object(subprocess, "run", forbidden),
    patch.object(sys, "argv", ["scripts/evaluate_live.py"]),
    contextlib.redirect_stdout(stdout),
):
    try:
        runpy.run_path(str(ROOT / "scripts/evaluate_live.py"), run_name="__main__")
    except SystemExit as exit_status:
        assert exit_status.code == 0
    else:
        raise AssertionError("Expected the actual command entrypoint to return explicitly")
(packet / "blocked-network-entrypoint.log").write_text(stdout.getvalue())
assert attempts == []
after = inventory()
assert before == after
write_json(
    packet / "verification.json",
    {
        "status": "verified_completed_live_entrypoint_preserves_evidence",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "actual_make_command_exit_code": completed.returncode,
        "campaign_files_and_mtimes_unchanged": len(before),
        "before_inventory_sha256": semantic_hash(before),
        "after_inventory_sha256": semantic_hash(after),
        "inprocess_network_and_subprocess_attempts": attempts,
        "finished_sha256": sha256_bytes((campaign / "finished.json").read_bytes()),
        "artifact_index_sha256": sha256_bytes((campaign / "artifact_hashes.json").read_bytes()),
        "source_hashes": {
            str(path.relative_to(ROOT)): sha256_bytes(path.read_bytes())
            for path in (
                Path(__file__),
                ROOT / "scripts/evaluate_live.py",
                ROOT / "Makefile",
                packet / "make-evaluate-live.log",
                packet / "blocked-network-entrypoint.log",
            )
        },
        "scope": "Command preservation on the actual completed corpus; not full offline production playback",
    },
)
print(
    f"Actual make evaluate-live preserved all {len(before)} campaign files and mtimes; blocked entrypoint attempted no network or subprocess work."
)
