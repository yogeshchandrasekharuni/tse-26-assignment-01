"""Small persistent local queue; one web worker and one shared production analysis service."""

import asyncio
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from housing.api.models import ErrorInfo, Job, Submission
from housing.api.registry import CAPTURES, frozen_snapshot
from housing.contracts.errors import HousingError
from housing.identity import ROOT
from housing.workflow.service import run_analysis

logger = logging.getLogger(__name__)


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def save(self, job: Job) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO jobs(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (job.id, job.model_dump_json()),
            )

    def get(self, job_id: str) -> Job | None:
        with sqlite3.connect(self.path) as db:
            record = db.execute("SELECT payload FROM jobs WHERE id=?", (job_id,)).fetchone()
        return Job.model_validate_json(record[0]) if record else None

    def all(self) -> tuple[Job, ...]:
        with sqlite3.connect(self.path) as db:
            records = db.execute("SELECT payload FROM jobs ORDER BY rowid DESC LIMIT 100").fetchall()
        return tuple(Job.model_validate_json(row[0]) for row in records)


class Jobs:
    def __init__(self, root: Path | None = None):
        self.root = root or ROOT / "artifacts/runtime/web"
        self.store = JobStore(self.root / "jobs.sqlite3")
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=8)

    def create(self, submission: Submission) -> Job:
        snapshot = frozen_snapshot()
        if submission.request.dataset_id != snapshot.dataset_id:
            raise HousingError("DATA_INVALID", "Choose the frozen local dataset", "web_submission")
        if not set(submission.request.visible_months).issubset(snapshot.months):
            raise HousingError(
                "DATA_INCOMPLETE", "The frozen feed must contain all twelve visible months", "web_submission"
            )
        if self.queue.full():
            raise HousingError(
                "BUDGET_EXCEEDED", "The local queue is full. Wait for an analysis to finish.", "web_queue"
            )
        if submission.capture_id and submission.request != CAPTURES[submission.capture_id].request():
            raise HousingError(
                "REPLAY_MISS",
                "Replay criteria must match that capture exactly. Restore its recorded criteria or run a new live analysis.",
                "web_submission",
            )
        now = datetime.now(UTC).isoformat()
        job = Job(
            id=uuid.uuid4().hex,
            state="queued",
            created_at_utc=now,
            updated_at_utc=now,
            submission=submission,
            output=None,
            error=None,
        )
        self.store.save(job)
        self.queue.put_nowait(job.id)
        return job

    def update(self, job: Job, **fields: object) -> Job:
        changed = Job.model_validate(
            {**job.model_dump(), **fields, "updated_at_utc": datetime.now(UTC).isoformat()}
        )
        self.store.save(changed)
        return changed

    def recover(self) -> None:
        for job in reversed(self.store.all()):
            if job.state == "running":
                self.update(
                    job,
                    state="failed",
                    error=ErrorInfo(
                        code="TOOL_ERROR",
                        stage="web_restart",
                        message="The server restarted during this analysis. Start a fresh run; the interrupted evidence is preserved.",
                    ),
                )
            elif job.state == "queued":
                self.queue.put_nowait(job.id)

    async def worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            job = self.store.get(job_id)
            if job is None:
                self.queue.task_done()
                continue
            job = self.update(job, state="running")
            try:
                submission = job.submission
                binding = CAPTURES[submission.capture_id] if submission.capture_id else None
                output = await run_analysis(
                    submission.request,
                    binding.snapshot() if binding else frozen_snapshot(),
                    mode=submission.mode,
                    capture=binding.directory if binding else None,
                    artifact_root=self.root / job.id / "runs",
                )
                self.update(job, state="completed", output=output)
            except HousingError as error:
                self.update(
                    job,
                    state="failed",
                    error=ErrorInfo(code=error.code, stage=error.stage, message=error.message),
                )
            except asyncio.CancelledError:
                self.update(
                    job,
                    state="failed",
                    error=ErrorInfo(
                        code="TOOL_ERROR",
                        stage="web_shutdown",
                        message="The local server stopped during this analysis. Its evidence is preserved; start a fresh run.",
                    ),
                )
                raise
            except Exception:
                logger.exception("Unexpected web analysis failure; job %s", job.id)
                self.update(
                    job,
                    state="failed",
                    error=ErrorInfo(
                        code="TOOL_ERROR",
                        stage="web_worker",
                        message="The local analysis failed. Inspect its preserved trace and start a fresh run.",
                    ),
                )
            finally:
                self.queue.task_done()
