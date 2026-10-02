"""Export finished live runs; optional polling never touches analysis execution."""

import argparse
import json
import re
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from httpx import HTTPError

from housing.identity import ROOT, semantic_hash, write_json
from housing.observability.langfuse import (
    EXPORT_VERSION,
    LocalLangfuse,
    observed_span_ids,
    project_capture,
    send_projection,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", type=Path, help="Registered local live capture directory")
    source.add_argument("--campaign", help="Local live campaign identifier")
    source.add_argument("--web", action="store_true", help="Finished live analyses from the local API")
    parser.add_argument("--include-web", action="store_true", help="Also observe local API live analyses")
    parser.add_argument("--dry-run", action="store_true", help="Write OTLP and hash manifest; no network")
    parser.add_argument(
        "--watch", action="store_true", help="Poll finished physical campaign runs every15seconds"
    )
    parser.add_argument("--verify", action="store_true", help="Read back every exported observation ID")
    args = parser.parse_args()
    if args.watch and not (args.campaign or args.web):
        parser.error("--watch requires --campaign or --web")
    if args.dry_run and args.watch:
        parser.error("--dry-run and --watch are separate operations")
    if args.campaign and re.fullmatch(r"[A-Za-z0-9-]+", args.campaign) is None:
        parser.error("Campaign must be a local identifier")
    settings = None if args.dry_run else LocalLangfuse.from_file(ROOT / "observability/langfuse/.env")
    destination_id = (
        semantic_hash([settings.base_url, settings.project_id, settings.public_key.get_secret_value()])
        if settings
        else None
    )
    completed: set[str] = set()
    while True:
        directories = (
            [ROOT / args.run]
            if args.run
            else []
            if args.web
            else sorted((ROOT / "artifacts/campaigns" / args.campaign).glob("cases/*/attempt-*/*/runs/*"))
        )
        if args.web or args.include_web:
            directories.extend(sorted((ROOT / "artifacts/runtime/web").glob("*/runs/*")))
        for directory in directories:
            if not (directory / "terminal.json").is_file():
                continue
            relative = str(directory.relative_to(ROOT))
            if relative in completed:
                continue
            manifest = json.loads((directory / "run-manifest.json").read_bytes())
            if manifest["mode"] != "live" and not args.run:
                print(f"Skipped historical replay capture: {directory.name}", flush=True)
                completed.add(relative)
                continue
            projection = project_capture(directory)
            destination = ROOT / "artifacts/observability/langfuse" / projection.trace_id
            receipt_path = destination / "receipt.json"
            digest = semantic_hash(projection)
            if receipt_path.exists():
                previous = json.loads(receipt_path.read_bytes())
                if previous["projection_sha256"] != digest:
                    if previous["status"] != "prepared_offline":
                        raise ValueError(
                            "Existing delivered projection changed; version the exporter and investigate"
                        )
                    archive = destination / "offline-drafts" / previous["projection_sha256"]
                    archive.mkdir(parents=True, exist_ok=True)
                    for name in ("projection.json", "traces.otlp.json", "receipt.json"):
                        shutil.copyfile(destination / name, archive / name)
                if (
                    previous["status"] in {"readback_verified", "accepted"}
                    and previous.get("destination_id") == destination_id
                    and not args.verify
                    and not args.dry_run
                ):
                    completed.add(relative)
                    continue
            write_json(destination / "projection.json", projection)
            write_json(destination / "traces.otlp.json", projection.otlp())
            status = "prepared_offline"
            readback_hash = None
            if settings:
                attempt_path = destination / "deliveries" / f"{time.time_ns()}.json"
                attempt = {
                    "started_at_utc": datetime.now(UTC).isoformat(),
                    "projection_sha256": digest,
                    "status": "sending",
                }
                write_json(attempt_path, attempt)
                try:
                    with settings.client() as client:
                        send_projection(projection, client)
                        status = "accepted"
                        attempt["status"] = status
                        write_json(attempt_path, attempt)
                        if args.verify:
                            expected = {projection.span_id(span.key) for span in projection.spans}
                            deadline = time.monotonic() + 45
                            while True:
                                observed = observed_span_ids(projection, client)
                                if observed == expected:
                                    status = "readback_verified"
                                    readback_hash = semantic_hash(sorted(observed))
                                    break
                                if time.monotonic() >= deadline:
                                    raise ValueError(
                                        f"Accepted, but readback differs: expected{len(expected)}, found{len(observed)}"
                                    )
                                time.sleep(2)
                    attempt["status"] = status
                    attempt["finished_at_utc"] = datetime.now(UTC).isoformat()
                    write_json(attempt_path, attempt)
                except Exception as error:
                    attempt["status"] = (
                        "readback_failed_after_acceptance" if status == "accepted" else "delivery_failed"
                    )
                    attempt["error_type"] = type(error).__name__
                    attempt["finished_at_utc"] = datetime.now(UTC).isoformat()
                    write_json(attempt_path, attempt)
                    if args.watch and isinstance(error, (ValueError, OSError, HTTPError)):
                        print(
                            f"Observer delivery interrupted ({type(error).__name__}); retrying after15seconds.",
                            flush=True,
                        )
                        break
                    raise
            receipt = {
                "schema_version": EXPORT_VERSION,
                "status": status,
                "run_path": projection.run_path,
                "trace_id": projection.trace_id,
                "projection_sha256": digest,
                "destination_id": destination_id,
                "observation_count": len(projection.spans),
                "readback_observation_ids_sha256": readback_hash,
                "exported_at_utc": datetime.now(UTC).isoformat(),
                "dashboard_url": f"{settings.base_url}/project/{settings.project_id}/traces/{projection.trace_id}"
                if settings
                else None,
                "interpretation": "Observation of historical live execution; no new model calls or evaluation outcome",
            }
            write_json(destination / "preparation.json" if args.dry_run else receipt_path, receipt)
            print(f"{status}: {projection.run_id} · {len(projection.spans)} observations", flush=True)
            completed.add(relative)
        if not args.watch:
            break
        time.sleep(15)


if __name__ == "__main__":
    main()
