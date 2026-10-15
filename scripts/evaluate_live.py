"""Preserve a completed live campaign; delegate unfinished work to the frozen runner."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from housing.evaluation.models import CaseResult, Cohort, HeadlineRow
from housing.identity import ROOT, sha256_bytes


def completed_capture(directory: Path) -> bool:
    """A final marker is insufficient: require all eligible identities and intact evidence."""
    if not (directory / "finished.json").exists():
        return False
    required = ("headline.json", "cases.jsonl", "artifact_hashes.json", "manifest.json")
    if not all((directory / name).is_file() for name in required):
        raise ValueError("Finish marker exists without complete aggregate files; inspect the original runner")
    rows = [HeadlineRow.model_validate(row) for row in json.loads((directory / "headline.json").read_bytes())]
    if not all(row.complete for row in rows):
        return False
    cohort_path = ROOT / "configs/headline-cohort-v1.json"
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    manifest = json.loads((directory / "manifest.json").read_bytes())
    cases = [
        CaseResult.model_validate_json(line) for line in (directory / "cases.jsonl").read_text().splitlines()
    ]
    expected = {(spec.mr, spec.base_id, seed) for spec in cohort.cases for seed in cohort.seeds}
    actual = {(case.mr_id, case.base_id, case.seed) for case in cases}
    finished = json.loads((directory / "finished.json").read_bytes())
    if (
        manifest["mode"] != "live"
        or manifest["cohort_sha256"] != sha256_bytes(cohort_path.read_bytes())
        or manifest["expected_comparisons"] != 900
        or finished["comparisons"] != 900
        or len(rows) != 10
        or {row.mr_id for row in rows} != {spec.mr for spec in cohort.cases}
        or any(row.completed_bases < 30 for row in rows)
        or len(cases) != 900
        or len(expected) != 900
        or actual != expected
        or any(case.status == "execution_error" for case in cases)
    ):
        raise ValueError("Closed live campaign does not contain the required complete paired workload")
    hashes = json.loads((directory / "artifact_hashes.json").read_bytes())
    inventory = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name != "artifact_hashes.json"
    }
    if set(hashes) != inventory:
        raise ValueError("Closed campaign file inventory differs from its saved artifact index")
    for relative, digest in hashes.items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory) or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError(f"Saved campaign evidence changed: {relative}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-execution-errors", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "artifacts/campaigns/headline-live-v1"
    if completed_capture(directory):
        print(
            "Verified all 900 saved comparisons; completed live evidence left unchanged. Use make reproduce for playback."
        )
        return 0
    if (directory / "finished.json").exists() and not args.retry_execution_errors:
        raise ValueError(
            "Closed campaign is incomplete; inspect its errors before explicit infrastructure retry"
        )
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    command = [
        sys.executable,
        "-u",
        "-m",
        "housing.evaluation",
        "run",
        "--cohort",
        "configs/headline-cohort-v1.json",
        "--directory",
        "artifacts/campaigns/headline-live-v1",
    ]
    if args.retry_execution_errors:
        command.append("--retry-execution-errors")
    return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        raise SystemExit(str(error)) from error
