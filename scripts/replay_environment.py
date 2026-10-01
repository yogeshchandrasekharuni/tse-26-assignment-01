"""Replay only the frozen environment proof, never claim full housing reproduction."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    reference = json.loads((ROOT / "configs/probe_reference.json").read_text())
    for name, expected in reference["required_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"REPLAY_MISS: frozen environment proof input changed: {name}")
    subprocess.run([sys.executable, "scripts/probe_fast_agent.py", "--stage", "replay", "--capture",
                    reference["seed_capture"]], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/probe_tool_playback.py", "--capture",
                    reference["native_tool_capture"]], cwd=ROOT, check=True)
    print("PASS: frozen environment proof replayed offline; full housing campaign reproduction remains pending.")


if __name__ == "__main__":
    main()
