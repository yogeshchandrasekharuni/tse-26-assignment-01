import argparse
import asyncio
from pathlib import Path

from housing.evaluation.aggregate import aggregate
from housing.evaluation.cohort import build_cohort
from housing.evaluation.runner import CampaignRunner
from housing.identity import ROOT, canonical_json


def main() -> int:
    parser = argparse.ArgumentParser(prog="housing-evaluation")
    parser.add_argument("command", choices=("freeze", "run", "summarize"))
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--mode", choices=("live", "replay"), default="live")
    parser.add_argument("--live-reference", type=Path)
    parser.add_argument("--retry-execution-errors", action="store_true")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    cohort_path = args.cohort.resolve() if args.cohort else None
    directory = args.directory.resolve() if args.directory else None
    if args.command == "freeze":
        if cohort_path is None:
            parser.error("freeze requires --cohort")
        cohort = build_cohort(cohort_path, pilot=args.pilot)
        print(
            canonical_json(
                {
                    "cohort": str(cohort_path.relative_to(ROOT)),
                    "eligible_cases": len(cohort.cases),
                    "coverage": cohort.coverage,
                }
            )
        )
        return 0
    if directory is None:
        parser.error("run/summarize requires --directory")
    if args.command == "run":
        if cohort_path is None:
            parser.error("run requires --cohort")
        runner = CampaignRunner(
            directory,
            cohort_path,
            mode=args.mode,
            live_reference=args.live_reference.resolve() if args.live_reference else None,
            retry_execution_errors=args.retry_execution_errors,
        )
        asyncio.run(runner.run())
    result = aggregate(
        directory, require_complete=not args.allow_incomplete, minimum_bases=3 if args.pilot else 30
    )
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
