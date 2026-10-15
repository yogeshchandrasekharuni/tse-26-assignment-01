"""Fail closed until the required evidence, report and visual verification agree."""

import json
from pathlib import Path

import pymupdf

from housing.evaluation.models import CaseResult, Cohort, HeadlineRow
from housing.identity import ROOT, sha256_bytes
from housing.reporting.campaign_observability import verify_campaign_observability
from housing.reporting.observability import verify_observability
from housing.reporting.plan_observability import verify_plan_observability
from housing.reporting.study_readback import (
    PROOF_PATH,
    verify_study_examples,
    verify_study_plan_observability,
    verify_study_readback,
)
from housing.reporting.usage import campaign_usage


def load(path: Path) -> object:
    return json.loads(path.read_bytes())


def check() -> None:
    if (ROOT / PROOF_PATH).is_file():
        verify_study_examples()
        verify_study_plan_observability()
        verify_study_readback()
    else:
        verify_observability()
        verify_plan_observability()
        verify_campaign_observability()
    campaign = ROOT / "artifacts/campaigns/headline-live-v1"
    headline_path = campaign / "headline.json"
    if not headline_path.exists():
        raise ValueError("Full live campaign has not produced its headline table")
    headline = [HeadlineRow.model_validate(row) for row in json.loads(headline_path.read_bytes())]
    if len(headline) != 10 or not all(row.complete and row.completed_bases >= 30 for row in headline):
        raise ValueError("Ten relations with at least thirty completed bases each are required")
    cohort_path = ROOT / "configs/headline-cohort-v1.json"
    cohort = Cohort.model_validate_json(cohort_path.read_bytes())
    if len(cohort.cases) != 300 or cohort.seeds != (104729, 130363, 155921):
        raise ValueError("Frozen cohort or paired seed panel differs")
    cases = [
        CaseResult.model_validate_json(line) for line in (campaign / "cases.jsonl").read_text().splitlines()
    ]
    if len(cases) != 900 or any(case.status == "execution_error" for case in cases):
        raise ValueError("All 900 logical comparisons must have completed eligible outcomes")
    expected_keys = {(case.mr, case.base_id, seed) for case in cohort.cases for seed in cohort.seeds}
    actual_keys = {(case.mr_id, case.base_id, case.seed) for case in cases}
    if actual_keys != expected_keys:
        raise ValueError("Logical comparisons have duplicate, missing or unexpected paired identities")
    for name, digest in json.loads((campaign / "artifact_hashes.json").read_bytes()).items():
        path = (campaign / name).resolve()
        if not path.is_relative_to(campaign) or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError(f"Campaign artifact integrity failed: {name}")
    for name in ("clean-checkout", "diagnosis", "pdf-qa"):
        path = ROOT / "reports/data" / f"{name}.json"
        if not path.is_file() or json.loads(path.read_bytes()).get("status") != "verified":
            raise ValueError(f"Required verified evidence missing: {path.relative_to(ROOT)}")
    clean = json.loads((ROOT / "reports/data/clean-checkout.json").read_bytes())
    if (
        clean.get("scope") != "headline"
        or clean.get("logical_comparisons") != 900
        or clean["headline_sha256"] != sha256_bytes(headline_path.read_bytes())
    ):
        raise ValueError("Clean-checkout evidence used a different headline table")
    diagnosis = json.loads((ROOT / "reports/data/diagnosis.json").read_bytes())
    if diagnosis.get("campaign_id") != campaign.name or diagnosis.get("headline_sha256") != sha256_bytes(
        headline_path.read_bytes()
    ):
        raise ValueError("Diagnosis belongs to a different campaign/table")
    for name, digest in diagnosis["supporting_artifact_hashes"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError(f"Diagnosed evidence changed: {name}")
    usage = json.loads((ROOT / "reports/data/headline-provider-usage.json").read_bytes())
    if campaign_usage(campaign) != usage:
        raise ValueError("Provider usage audit differs from current raw live evidence")
    for step in clean["commands"]:
        if step["exit_code"] or sha256_bytes((ROOT / step["log"]).read_bytes()) != step["log_sha256"]:
            raise ValueError("Clean-checkout command/log verification failed")
    pdf = ROOT / "output/pdf/housing-report.pdf"
    report_manifest = json.loads(pdf.with_suffix(".manifest.json").read_bytes())
    if report_manifest["pdf_sha256"] != sha256_bytes(pdf.read_bytes()):
        raise ValueError("Report bytes differ from its build manifest")
    for name, digest in report_manifest["inputs"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError(f"Report input changed after its build: {name}")
    reproduction = ROOT / report_manifest["full_reproduction"]
    comparison = json.loads((reproduction / "reproduction-comparison.json").read_bytes())
    if comparison["status"] != "matched" or comparison["logical_comparisons"] != 900:
        raise ValueError("Report is not linked to a complete matched offline reproduction")
    qa = json.loads((ROOT / "reports/data/pdf-qa.json").read_bytes())
    if qa["pdf_sha256"] != sha256_bytes(pdf.read_bytes()) or qa["inspected_pages"] != list(range(1, 13)):
        raise ValueError("Final PDF differs from visually inspected twelve pages")
    with pymupdf.open(pdf) as document:
        if len(document) != 12 or any("WORKING DRAFT" in page.get_text() for page in document):
            raise ValueError("Final report must contain twelve final, non-draft pages")
    for path in (
        "README.md",
        "NOTEBOOK.md",
        "AI_USE.md",
        "DESIGN_NOTE.md",
        "DESIGN.md",
        ".impeccable/design.json",
        ".impeccable/review/finish-review.md",
        ".impeccable/review/finish-verdict.md",
        "uv.lock",
        "frontend/package-lock.json",
        "reports/data/headline-provider-usage.json",
    ):
        if not (ROOT / path).is_file():
            raise ValueError(f"Missing deliverable: {path}")
    print(
        "Submission evidence verified: 10 MRs / 300 bases / 900 pairs; clean offline reproduction; 12 inspected PDF pages."
    )


if __name__ == "__main__":
    try:
        check()
    except ValueError as error:
        raise SystemExit(str(error)) from error
