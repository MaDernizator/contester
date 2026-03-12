from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from contester.extensions import db
from contester.judging.python_runner import (
    PythonExecutionStatus,
    PythonRunner,
)
from contester.models.problem import Problem
from contester.models.submission import Submission, SubmissionVerdict
from contester.models.test_case import TestCase


def _normalize_output(output: str) -> str:
    normalized_lines = [
        line.rstrip()
        for line in output.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]

    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()

    return "\n".join(normalized_lines)


def _truncate_text(value: str, max_length: int = 4000) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length] + "\n...[truncated]"


class JudgeService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.python_runner = PythonRunner()

    def judge_submission(self, submission_id) -> Submission:
        submission = db.session.scalar(
            select(Submission)
            .options(
                selectinload(Submission.user),
                selectinload(Submission.problem).selectinload(Problem.contest),
            )
            .where(Submission.id == submission_id)
        )
        if submission is None:
            raise ValueError("Submission not found.")

        test_cases = db.session.execute(
            select(TestCase)
            .where(
                TestCase.problem_id == submission.problem_id,
                TestCase.is_active.is_(True),
            )
            .order_by(TestCase.position.asc(), TestCase.created_at.asc())
        ).scalars().all()

        submission.mark_running(total_test_count=len(test_cases))
        db.session.commit()

        if not test_cases:
            submission.finish(
                verdict=SubmissionVerdict.NO_TESTS,
                passed_test_count=0,
                total_test_count=0,
                judge_log="No active test cases configured for this problem.",
            )
            db.session.commit()
            return submission

        max_execution_time_ms = 0
        passed_test_count = 0

        try:
            with tempfile.TemporaryDirectory(dir=self.workspace_root) as temporary_dir:
                workspace_dir = Path(temporary_dir)

                for test_case in test_cases:
                    result = self.python_runner.execute(
                        source_code=submission.source_code,
                        input_data=test_case.input_data,
                        time_limit_ms=submission.problem.time_limit_ms,
                        workspace_dir=workspace_dir,
                    )
                    max_execution_time_ms = max(
                        max_execution_time_ms,
                        result.execution_time_ms,
                    )

                    if result.status == PythonExecutionStatus.TIME_LIMIT_EXCEEDED:
                        submission.finish(
                            verdict=SubmissionVerdict.TIME_LIMIT_EXCEEDED,
                            passed_test_count=passed_test_count,
                            total_test_count=len(test_cases),
                            failed_test_position=test_case.position,
                            execution_time_ms=result.execution_time_ms,
                            judge_log=f"Time limit exceeded on test case {test_case.position}.",
                        )
                        db.session.commit()
                        return submission

                    if result.status == PythonExecutionStatus.RUNTIME_ERROR:
                        submission.finish(
                            verdict=SubmissionVerdict.RUNTIME_ERROR,
                            passed_test_count=passed_test_count,
                            total_test_count=len(test_cases),
                            failed_test_position=test_case.position,
                            execution_time_ms=result.execution_time_ms,
                            judge_log=_truncate_text(result.stderr or "Runtime error."),
                        )
                        db.session.commit()
                        return submission

                    actual_output = _normalize_output(result.stdout)
                    expected_output = _normalize_output(test_case.expected_output)

                    if actual_output != expected_output:
                        submission.finish(
                            verdict=SubmissionVerdict.WRONG_ANSWER,
                            passed_test_count=passed_test_count,
                            total_test_count=len(test_cases),
                            failed_test_position=test_case.position,
                            execution_time_ms=result.execution_time_ms,
                            judge_log=f"Wrong answer on test case {test_case.position}.",
                        )
                        db.session.commit()
                        return submission

                    passed_test_count += 1

            submission.finish(
                verdict=SubmissionVerdict.ACCEPTED,
                passed_test_count=passed_test_count,
                total_test_count=len(test_cases),
                execution_time_ms=max_execution_time_ms,
                judge_log="Accepted.",
            )
            db.session.commit()
            return submission

        except Exception as error:
            db.session.rollback()

            submission = db.session.get(Submission, submission_id)
            if submission is None:
                raise

            submission.finish(
                verdict=SubmissionVerdict.INTERNAL_ERROR,
                passed_test_count=passed_test_count,
                total_test_count=len(test_cases),
                execution_time_ms=max_execution_time_ms or None,
                judge_log=_truncate_text(str(error) or "Internal judge error."),
            )
            db.session.commit()
            return submission