"""Reproduce one captured leg, including natural failures, through strict production playback."""

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime

from housing.contracts.errors import HousingError
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import load_snapshot
from housing.evaluation.models import CaseResult, Cohort
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, sha256_bytes, write_json
from housing.workflow.service import run_analysis


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="headline-live-v1")
    parser.add_argument("--case", required=True)
    parser.add_argument("--leg", choices=("source", "followup"), default="followup")
    args = parser.parse_args()
    if any(re.fullmatch(r"[A-Za-z0-9-]+", value) is None for value in (args.campaign, args.case)):
        raise ValueError("Campaign and case must be local identifiers")
    campaign = ROOT / "artifacts/campaigns" / args.campaign
    case_path = campaign / "cases" / args.case / "result.json"
    case = CaseResult.model_validate_json(case_path.read_bytes())
    campaign_manifest = json.loads((campaign / "manifest.json").read_bytes())
    cohort = Cohort.model_validate_json((ROOT / campaign_manifest["cohort_path"]).read_bytes())
    spec = next(c for c in cohort.cases if c.mr == case.mr_id and c.base_id == case.base_id)
    snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
    request = updated_request(spec.source_request, seed=case.seed)
    if args.leg == "followup":
        snapshot, request = transform(
            snapshot, request, spec.recipe, DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
        )
    leg = case.source if args.leg == "source" else case.followup
    capture = ROOT / leg.run_path
    if not capture.resolve().is_relative_to(campaign.resolve()):
        raise ValueError("Capture escapes its campaign")
    destination = ROOT / "artifacts/rca" / args.case / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    observed_code = None
    try:
        await run_analysis(
            request, snapshot, mode="replay", capture=capture, artifact_root=destination / "runs"
        )
    except HousingError as error:
        observed_code = error.code
    run = next((destination / "runs").iterdir())
    terminal = json.loads((run / "terminal.json").read_bytes())
    expected_terminal = json.loads((capture / "terminal.json").read_bytes())
    if (
        observed_code != leg.error_code
        or terminal["status"] != expected_terminal["status"]
        or terminal["model_decisions"] != expected_terminal["model_decisions"]
        or terminal["network_attempts"]
        or terminal.get("canonical_sha256") != expected_terminal.get("canonical_sha256")
    ):
        raise ValueError("Single-leg playback does not reproduce the captured outcome")
    write_json(
        destination / "comparison.json",
        {
            "status": "matched",
            "scope": "one captured leg; not a new statistical comparison",
            "case": str(case_path.relative_to(ROOT)),
            "case_sha256": sha256_bytes(case_path.read_bytes()),
            "capture": str(capture.relative_to(ROOT)),
            "replay": str(run.relative_to(ROOT)),
            "expected_error_code": leg.error_code,
            "observed_error_code": observed_code,
            "model_decisions": terminal["model_decisions"],
            "network_attempts": terminal["network_attempts"],
        },
    )
    print(f"Matched {args.case}/{args.leg}: {terminal['status']} / {observed_code or 'canonical match'}")
    print(destination.relative_to(ROOT))


asyncio.run(main())
