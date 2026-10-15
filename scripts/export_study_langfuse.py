"""Export recorded captures to the separate local dashboard and read them back."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from pydantic import SecretStr

from housing.identity import ROOT, semantic_hash
from housing.observability.langfuse import LocalLangfuse, observed_span_ids, send_projection
from housing.observability.langfuse_plan import PROJECTION_REVISION, project_capture

WORK_DIRECTORY = ROOT / ".cache/langfuse-study-export"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample", action="store_true", help="Verify one capture instead of the full inventory"
    )
    args = parser.parse_args()
    work_directory = WORK_DIRECTORY / ("sample" if args.sample else "full")
    env_path = ROOT / "observability/langfuse/.env.study"
    values = dict(
        line.strip().split("=", 1)
        for line in env_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if (
        values["LANGFUSE_BASE_URL"] != "http://localhost:19310"
        or values["LANGFUSE_PROJECT_ID"] != "housing-trajectories"
    ):
        raise ValueError("The study exporter is restricted to its separate local dashboard")
    settings = LocalLangfuse(
        base_url=values["LANGFUSE_BASE_URL"],
        public_key=SecretStr(values["LANGFUSE_PUBLIC_KEY"]),
        secret_key=SecretStr(values["LANGFUSE_SECRET_KEY"]),
        project_id=values["LANGFUSE_PROJECT_ID"],
    )
    destination_id = semantic_hash(
        [settings.base_url, settings.project_id, settings.public_key.get_secret_value()]
    )
    campaign = ROOT / "artifacts/campaigns/headline-live-v1"
    physical = sorted(
        path for path in campaign.glob("cases/*/attempt-*/*/runs/*") if (path / "terminal.json").is_file()
    )
    runtime = json.loads((campaign / "runtime.json").read_bytes())
    if len(physical) != runtime["physical_analysis_attempts"]:
        raise ValueError("Closed capture inventory differs from the completed campaign")
    examples = json.loads((ROOT / "artifacts/observability/demo-index.json").read_bytes())["examples"]
    runs = sorted(set(physical) | {ROOT / row["run_path"] for row in examples})
    if args.sample:
        runs = physical[:1]
    started = datetime.now(UTC).isoformat()

    def export(run: Path) -> tuple[str, int]:
        projection = project_capture(run)
        expected = {projection.span_id(span.key) for span in projection.spans}
        with settings.client() as client:
            # Read the server even on a retry: cached receipts do not prove that
            # a recreated dashboard still contains the observations.
            observed = observed_span_ids(projection, client)
            if observed != expected:
                send_projection(projection, client)
                deadline = time.monotonic() + 120
                while True:
                    observed = observed_span_ids(projection, client)
                    if observed == expected:
                        break
                    if time.monotonic() >= deadline:
                        raise ValueError(f"Readback mismatch: {len(observed)}/{len(expected)} observations")
                    time.sleep(1)
        receipt = {
            "schema_version": "housing-langfuse-1",
            "projection_revision": PROJECTION_REVISION,
            "status": "readback_verified",
            "run_path": projection.run_path,
            "trace_id": projection.trace_id,
            "projection_sha256": semantic_hash(projection),
            "destination_id": destination_id,
            "observation_count": len(expected),
            "readback_observation_ids_sha256": semantic_hash(sorted(observed)),
            "exported_at_utc": datetime.now(UTC).isoformat(),
            "dashboard_url": f"{settings.base_url}/project/{settings.project_id}/traces/{projection.trace_id}",
            "interpretation": "Readback of recorded projection; no new model calls or evaluation outcomes",
        }
        directory = work_directory / "proof" / projection.trace_id
        write_json(directory / "projection.json", projection.model_dump(mode="json"))
        write_json(directory / "receipt.json", receipt)
        return projection.run_path, len(expected)

    failures = []
    completed = 0
    observations = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(export, run): run for run in runs}
        for future in as_completed(futures):
            try:
                _, count = future.result()
                completed += 1
                observations += count
            except Exception as error:  # noqa: BLE001 - retain every failed capture for the final audit
                failures.append(
                    {"run_path": str(futures[future].relative_to(ROOT)), "type": type(error).__name__}
                )
            if (completed + len(failures)) % 25 == 0:
                print(f"Readback {completed}/{len(runs)}; failures {len(failures)}", flush=True)
    result = {
        "started_at_utc": started,
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "scope": "sample" if args.sample else "complete_inventory",
        "campaign_captures": len(physical),
        "total_captures": len(runs),
        "completed": completed,
        "observations": observations,
        "failures": failures,
    }
    write_json(work_directory / "result.json", result)
    if failures or completed != len(runs):
        raise ValueError("Study dashboard export was incomplete; see its local result file")
    print(f"Verified {completed} captures in the separate dashboard; no model calls were made.")


if __name__ == "__main__":
    main()
