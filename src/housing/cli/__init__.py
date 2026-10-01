"""Repository CLI; API and evaluation will share the same analysis service."""

import argparse
import asyncio
from pathlib import Path

from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH, freeze
from housing.data.store import load_snapshot
from housing.identity import canonical_json
from housing.workflow.service import run_analysis


def main() -> int:
    parser = argparse.ArgumentParser(prog="housing")
    parser.add_argument("command", choices=["data", "analyze"])
    parser.add_argument("--request", type=Path)
    parser.add_argument("--mode", choices=["live", "replay"], default="live")
    parser.add_argument("--capture", type=Path)
    parser.add_argument(
        "--inject-index-omission",
        action="store_true",
        help="Labeled auxiliary control: omit the first requested ZIP in the first visible month from the index",
    )
    args = parser.parse_args()
    if args.command == "data":
        manifest = freeze()
        print(
            canonical_json(
                {
                    "dataset_id": manifest.dataset_id,
                    "rows": manifest.actual_rows,
                    "sha256": manifest.snapshot_sha256,
                    "verified": True,
                }
            )
        )
    elif args.command == "analyze":
        if args.request is None:
            parser.error("analyze requires --request")
        request = AnalysisRequest.model_validate_json(args.request.read_bytes())
        snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
        if args.inject_index_omission:
            snapshot = snapshot.omit_index_partitions(
                frozenset({(request.visible_months[0], request.criteria.zips[0])})
            )
        output = asyncio.run(run_analysis(request, snapshot, mode=args.mode, capture=args.capture))
        print(canonical_json(output))
    return 0
