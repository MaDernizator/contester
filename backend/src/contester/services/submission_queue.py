from __future__ import annotations

import time
from pathlib import Path

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
        cxx_compiler: str,
        cpp_compile_timeout_sec: int,
    ) -> None:
        self.judge_service = JudgeService(
            workspace_root,
            execution_backend=execution_backend,
            docker_binary=docker_binary,
            docker_image=docker_image,
            cxx_compiler=cxx_compiler,
            cpp_compile_timeout_sec=cpp_compile_timeout_sec,
        )

    @classmethod
    def from_app_config(cls) -> "SubmissionQueueService":
        return cls(
            workspace_root=Path(current_app.config["JUDGE_WORKSPACE_DIR"]),
            execution_backend=current_app.config["JUDGE_EXECUTION_BACKEND"],
            docker_binary=current_app.config["JUDGE_DOCKER_BINARY"],
            docker_image=current_app.config["JUDGE_DOCKER_IMAGE"],
            cxx_compiler=current_app.config["CXX_COMPILER"],
            cpp_compile_timeout_sec=current_app.config["CPP_COMPILE_TIMEOUT_SEC"],
        )

    def fetch_next_pending_submission_id(self):
        statement = (
            select(Submission.id)
            .where(Submission.status == SubmissionStatus.PENDING)
            .order_by(Submission.created_at.asc(), Submission.id.asc())
            .limit(1)
        )
        return db.session.scalar(statement)

    def process_next_submission(self) -> bool:
        submission_id = self.fetch_next_pending_submission_id()
        if submission_id is None:
            return False

        self.judge_service.judge_submission(submission_id)
        return True

    def run_once(self) -> int:
        processed = 0

        while self.process_next_submission():
            processed += 1

        return processed

    def run_forever(self, *, poll_interval_sec: int) -> None:
        while True:
            processed_any = self.process_next_submission()
            if not processed_any:
                time.sleep(poll_interval_sec)