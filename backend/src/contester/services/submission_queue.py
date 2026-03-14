from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from flask import current_app
from sqlalchemy import select

from contester.extensions import db
from contester.judging import JudgeService
from contester.models.submission import Submission, SubmissionStatus


class SubmissionQueueService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        execution_backend: str,
        docker_binary: str,
        docker_image: str,
        docker_shared_volume: str,
        docker_shared_mount_path: str,
        cxx_compiler: str,
        cpp_compile_timeout_sec: int,
        running_timeout_sec: int,
    ) -> None:
        self.judge_service = JudgeService(
            workspace_root,
            execution_backend=execution_backend,
            docker_binary=docker_binary,
            docker_image=docker_image,
            docker_shared_volume=docker_shared_volume,
            docker_shared_mount_path=docker_shared_mount_path,
            cxx_compiler=cxx_compiler,
            cpp_compile_timeout_sec=cpp_compile_timeout_sec,
        )
        self.running_timeout_sec = running_timeout_sec

    @classmethod
    def from_app_config(cls) -> "SubmissionQueueService":
        return cls(
            workspace_root=Path(current_app.config["JUDGE_WORKSPACE_DIR"]),
            execution_backend=current_app.config["JUDGE_EXECUTION_BACKEND"],
            docker_binary=current_app.config["JUDGE_DOCKER_BINARY"],
            docker_image=current_app.config["JUDGE_DOCKER_IMAGE"],
            docker_shared_volume=current_app.config["JUDGE_DOCKER_SHARED_VOLUME"],
            docker_shared_mount_path=current_app.config["JUDGE_DOCKER_SHARED_MOUNT_PATH"],
            cxx_compiler=current_app.config["CXX_COMPILER"],
            cpp_compile_timeout_sec=current_app.config["CPP_COMPILE_TIMEOUT_SEC"],
            running_timeout_sec=int(
                current_app.config["JUDGE_RUNNING_SUBMISSION_TIMEOUT_SEC"]
            ),
        )

    def claim_next_pending_submission_id(self) -> UUID | None:
        statement = (
            select(Submission)
            .where(Submission.status == SubmissionStatus.PENDING)
            .order_by(Submission.created_at.asc(), Submission.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        submission = db.session.execute(statement).scalars().first()
        if submission is None:
            return None

        submission.mark_running(total_test_count=0)
        db.session.commit()
        return submission.id

    def requeue_stale_running_submissions(self, *, timeout_sec: int | None = None) -> int:
        effective_timeout_sec = timeout_sec or self.running_timeout_sec
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=effective_timeout_sec)

        statement = (
            select(Submission)
            .where(
                Submission.status == SubmissionStatus.RUNNING,
                Submission.updated_at < cutoff,
            )
            .order_by(Submission.updated_at.asc(), Submission.id.asc())
        )

        stale_submissions = db.session.execute(statement).scalars().all()
        if not stale_submissions:
            return 0

        for submission in stale_submissions:
            submission.requeue(
                judge_log="Submission was re-queued after stale running timeout."
            )

        db.session.commit()
        return len(stale_submissions)

    def process_next_submission(self) -> bool:
        submission_id = self.claim_next_pending_submission_id()
        if submission_id is None:
            return False

        self.judge_service.judge_submission(submission_id)
        return True

    def run_once(self, *, running_timeout_sec: int | None = None) -> int:
        self.requeue_stale_running_submissions(timeout_sec=running_timeout_sec)

        processed = 0
        while self.process_next_submission():
            processed += 1

        return processed

    def run_forever(
        self,
        *,
        poll_interval_sec: int,
        running_timeout_sec: int | None = None,
    ) -> None:
        while True:
            recovered = self.requeue_stale_running_submissions(
                timeout_sec=running_timeout_sec
            )
            processed_any = self.process_next_submission()

            if not processed_any and recovered == 0:
                time.sleep(poll_interval_sec)
