"""Sequential local campaign runner. Live and replay call the same production service."""

import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from housing.contracts.errors import HousingError
from housing.contracts.output import AnalysisOutput
from housing.contracts.request import AnalysisRequest
from housing.data.generate import CSV_PATH, MANIFEST_PATH
from housing.data.models import DatasetManifest
from housing.data.store import Snapshot, load_snapshot
from housing.evaluation.cohort import evaluation_inputs
from housing.evaluation.compare import compare
from housing.evaluation.models import CaseResult, CaseSpec, Cohort, LegOutcome
from housing.evaluation.transforms import transform, updated_request
from housing.identity import ROOT, semantic_hash, sha256_bytes, write_json
from housing.workflow.boundary import execution_identity
from housing.workflow.service import run_analysis

CONTRACT_FAULTS = frozenset({"AGENT_OUTPUT_INVALID", "AGENT_POLICY_ERROR", "BUDGET_EXCEEDED"})


def relative(path: Path) -> str:
    if not path.is_relative_to(ROOT):
        raise ValueError("Campaign evidence must remain inside the repository")
    return str(path.relative_to(ROOT))


def load_output(directory: Path) -> AnalysisOutput:
    """Live-only resume of an already completed source; never used by replay."""
    return AnalysisOutput.model_validate_json((directory / "output.json").read_bytes())


class CampaignRunner:
    def __init__(
        self,
        directory: Path,
        cohort_path: Path,
        *,
        mode: Literal["live", "replay"],
        live_reference: Path | None = None,
        retry_execution_errors: bool = False,
    ):
        self.directory, self.cohort_path, self.mode = directory, cohort_path, mode
        self.cohort = Cohort.model_validate_json(cohort_path.read_bytes())
        self.live_reference = live_reference
        self.retry_execution_errors = retry_execution_errors
        self.snapshot = load_snapshot(CSV_PATH, MANIFEST_PATH)
        self.dataset_manifest = DatasetManifest.model_validate_json(MANIFEST_PATH.read_bytes())
        self.cache: dict[str, tuple[LegOutcome, AnalysisOutput, str]] = {}

    def manifest(self) -> dict[str, object]:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        return {
            "version": "campaign-2",
            "campaign_id": self.directory.name,
            "mode": self.mode,
            "live_campaign_id": self.live_reference.name if self.live_reference else self.directory.name,
            "live_reference": relative(self.live_reference) if self.live_reference else None,
            "cohort_path": relative(self.cohort_path),
            "cohort_sha256": sha256_bytes(self.cohort_path.read_bytes()),
            "evaluation_inputs": evaluation_inputs(),
            "execution_boundaries": {
                str(seed): semantic_hash(
                    execution_identity(
                        updated_request(self.cohort.cases[0].source_request, seed=seed), self.snapshot
                    ).inputs
                )
                for seed in self.cohort.seeds
            },
            "python": platform.python_version(),
            "git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "git_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
            "launch_command": [sys.executable, "-m", "housing.evaluation", *sys.argv[1:]],
            "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
            "expected_comparisons": len(self.cohort.cases) * len(self.cohort.seeds),
            "seeds": self.cohort.seeds,
            "source_reuse": "completed execution with identical full production identity; explicit per-case lineage",
            "followup_cache": "disabled; each new logical follow-up executes the service",
        }

    def prepare(self) -> None:
        if os.environ.get("PYTHONHASHSEED") != "0":
            raise ValueError("Campaign must launch with PYTHONHASHSEED=0")
        if self.cohort.evaluation_inputs != evaluation_inputs():
            raise ValueError(
                "Evaluation code/catalog changed since cohort freeze; create a new cohort version"
            )
        if self.cohort.source_snapshot_sha256 != self.snapshot.source_sha256:
            raise ValueError("Cohort snapshot differs")
        if self.mode == "replay" and self.live_reference is None:
            raise ValueError("Replay campaign requires a genuine live reference")
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / "manifest.json"
        manifest = self.manifest()
        if target.exists():
            existing = json.loads(target.read_bytes())
            ignored = {"git_revision", "git_dirty", "launch_command"}
            if {k: v for k, v in existing.items() if k not in ignored} != {
                k: v for k, v in json.loads(json.dumps(manifest)).items() if k not in ignored
            }:
                raise ValueError("Existing campaign belongs to different code/config/cohort; never overwrite")
        else:
            write_json(target, manifest)
            write_json(self.directory / "started.json", {"started_at_utc": datetime.now(UTC).isoformat()})

    async def leg(
        self, request: AnalysisRequest, snapshot: Snapshot, location: Path, *, capture: Path | None
    ) -> tuple[LegOutcome, AnalysisOutput | None]:
        key = semantic_hash(execution_identity(request, snapshot))
        if location.exists():
            raise ValueError("Physical execution already exists; preserve it and use a new attempt")
        location.mkdir(parents=True)
        output: AnalysisOutput | None = None
        error: HousingError | None = None
        started = time.perf_counter_ns()
        try:
            output = await run_analysis(
                request,
                snapshot,
                mode=self.mode,
                capture=capture,
                artifact_root=location / "runs",
                campaign_id=self.live_reference.name if self.live_reference else self.directory.name,
            )
        except HousingError as failure:
            error = failure
        elapsed = time.perf_counter_ns() - started
        runs = list((location / "runs").glob("*"))
        if len(runs) != 1:
            raise ValueError("Analysis did not preserve exactly one physical run")
        run = runs[0]
        outcome = LegOutcome(
            execution_key=key,
            status="failed" if error else "completed",
            run_id=run.name,
            run_path=relative(run),
            capture_path=relative(capture) if capture else None,
            request_sha256=semantic_hash(request),
            view_sha256=snapshot.view_sha256,
            requested_seed=request.seed,
            effective_seed=output.metadata.effective_seed
            if output
            else request.seed
            if any((run / "cassettes").glob("*.json"))
            else None,
            canonical_sha256=semantic_hash(output.canonical) if output else None,
            output_sha256=semantic_hash(output) if output else None,
            error_code=error.code if error else None,
            error_stage=error.stage if error else None,
            duration_ns=elapsed,
        )
        write_json(location / "record.json", outcome)
        return outcome, output

    async def case(
        self, spec: CaseSpec, seed: int, attempt: Path, reference: CaseResult | None
    ) -> CaseResult:
        request = updated_request(spec.source_request, seed=seed)
        changed, followup_request = transform(self.snapshot, request, spec.recipe, self.dataset_manifest)
        if changed.view_sha256 != spec.followup_view_sha256 or followup_request != updated_request(
            spec.followup_request, seed=seed
        ):
            raise ValueError("Materialized input differs from frozen preflight")
        reuse_key = semantic_hash(execution_identity(request, self.snapshot))
        cached = self.cache.get(reuse_key)
        source_reused: str | None = None
        source_output: AnalysisOutput | None
        if cached:
            source, source_output, source_reused = cached
        else:
            source, source_output = await self.leg(
                request,
                self.snapshot,
                attempt / "source",
                capture=ROOT / reference.source.run_path if reference else None,
            )
            if source_output:
                self.cache[reuse_key] = (source, source_output, relative(attempt / "source/record.json"))
        followup, followup_output = await self.leg(
            followup_request,
            changed,
            attempt / "followup",
            capture=ROOT / reference.followup.run_path if reference else None,
        )
        errors = tuple(leg.error_code for leg in (source, followup) if leg.error_code is not None)
        comparison = None
        violation_kind: Literal["relation", "output_contract"] | None = None
        status: Literal["pass", "violation", "execution_error"]
        if any(code not in CONTRACT_FAULTS for code in errors):
            status = "execution_error"
        elif errors:
            status, violation_kind = "violation", "output_contract"
        else:
            if source_output is None or followup_output is None:
                raise ValueError("Successful pair lacks outputs")
            comparison = compare(spec, source_output, followup_output)
            status = comparison.status
            violation_kind = "relation" if status == "violation" else None
        return CaseResult(
            schema_version="case-2",
            campaign_id=self.directory.name,
            live_campaign_id=self.live_reference.name if self.live_reference else self.directory.name,
            mode=self.mode,
            mr_id=spec.mr,
            mr_version="1.0",
            base_id=spec.base_id,
            slice_group=spec.slice_group,
            base_semantic_sha256=spec.base_query_sha256,
            cohort_case_sha256=semantic_hash(spec),
            transform_sha256=semantic_hash(spec.recipe),
            seed=seed,
            eligibility_path=relative(self.cohort_path),
            source=source,
            followup=followup,
            source_reused_from=source_reused,
            status=status,
            violation_kind=violation_kind,
            reason_codes=errors,
            comparison=comparison,
        )

    async def run(self) -> None:
        self.prepare()
        completed = 0
        for spec in self.cohort.cases:
            for seed in self.cohort.seeds:
                name = f"{spec.mr}-{spec.base_id}-s{seed}"
                location = self.directory / "cases" / name
                result_path = location / "result.json"
                if result_path.exists():
                    result = CaseResult.model_validate_json(result_path.read_bytes())
                    if result.cohort_case_sha256 != semantic_hash(spec) or result.seed != seed:
                        raise ValueError("Saved case identity differs")
                    # Resume may reuse genuine completed live sources. Replay never loads live
                    # final outputs; a new replay campaign must rerun its production tools.
                    if self.mode == "replay":
                        raise ValueError("Replay must start in a fresh output directory")
                    if result.source.status == "completed":
                        output = load_output(ROOT / result.source.run_path)
                        if semantic_hash(output) != result.source.output_sha256:
                            raise ValueError("Saved live source output integrity differs")
                        self.cache[result.source.execution_key] = (
                            result.source,
                            output,
                            relative(result_path),
                        )
                    if not (self.retry_execution_errors and result.status == "execution_error"):
                        completed += 1
                        continue
                reference = None
                if self.live_reference:
                    reference = CaseResult.model_validate_json(
                        (self.live_reference / "cases" / name / "result.json").read_bytes()
                    )
                    if reference.mode != "live" or reference.cohort_case_sha256 != semantic_hash(spec):
                        raise ValueError("Replay case lacks exact live lineage")
                location.mkdir(parents=True, exist_ok=True)
                existing = sorted(location.glob("attempt-*"))
                attempt = location / f"attempt-{len(existing) + 1:03d}"
                result = await self.case(spec, seed, attempt, reference)
                write_json(attempt / "case.json", result)
                write_json(result_path, result)
                completed += 1
                write_json(
                    self.directory / "progress.json",
                    {
                        "completed_comparisons": completed,
                        "expected_comparisons": len(self.cohort.cases) * len(self.cohort.seeds),
                        "last_case": name,
                        "last_status": result.status,
                        "updated_at_utc": datetime.now(UTC).isoformat(),
                    },
                )
                print(
                    f"{self.mode} {completed}/{len(self.cohort.cases) * len(self.cohort.seeds)} {name}: {result.status}",
                    flush=True,
                )
        write_json(
            self.directory / "finished.json",
            {"finished_at_utc": datetime.now(UTC).isoformat(), "comparisons": completed},
        )
