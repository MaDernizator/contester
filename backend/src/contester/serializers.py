from __future__ import annotations

from datetime import datetime, timezone

from contester.models.contest import Contest
from contester.models.problem import Problem
from contester.models.submission import Submission
from contester.models.test_case import TestCase
from contester.models.user import User


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_datetime(value: datetime) -> str:
    return _ensure_utc_datetime(value).isoformat().replace("+00:00", "Z")


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _serialize_datetime(value)


def _get_contest_phase(contest: Contest) -> str:
    now = datetime.now(timezone.utc)
    starts_at = _ensure_utc_datetime(contest.starts_at) if contest.starts_at is not None else None
    ends_at = _ensure_utc_datetime(contest.ends_at) if contest.ends_at is not None else None

    if ends_at is not None and now >= ends_at:
        return "finished"

    if starts_at is not None and now < starts_at:
        return "upcoming"

    if starts_at is not None and (ends_at is None or starts_at <= now < ends_at):
        return "running"

    return "unscheduled"


def serialize_user(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": _serialize_datetime(user.created_at),
        "updated_at": _serialize_datetime(user.updated_at),
    }


def serialize_user_summary(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
    }


def serialize_contest_summary(contest: Contest) -> dict[str, object]:
    return {
        "id": str(contest.id),
        "title": contest.title,
        "slug": contest.slug,
        "status": contest.status.value,
    }


def serialize_contest(contest: Contest) -> dict[str, object]:
    return {
        "id": str(contest.id),
        "title": contest.title,
        "slug": contest.slug,
        "description": contest.description,
        "status": contest.status.value,
        "starts_at": _serialize_optional_datetime(contest.starts_at),
        "ends_at": _serialize_optional_datetime(contest.ends_at),
        "phase": _get_contest_phase(contest),
        "created_at": _serialize_datetime(contest.created_at),
        "updated_at": _serialize_datetime(contest.updated_at),
        "created_by": serialize_user_summary(contest.created_by),
    }


def serialize_problem_summary(problem: Problem) -> dict[str, object]:
    return {
        "id": str(problem.id),
        "contest_id": str(problem.contest_id),
        "code": problem.code,
        "title": problem.title,
        "position": problem.position,
        "status": problem.status.value,
        "time_limit_ms": problem.time_limit_ms,
        "memory_limit_mb": problem.memory_limit_mb,
        "created_at": _serialize_datetime(problem.created_at),
        "updated_at": _serialize_datetime(problem.updated_at),
    }


def serialize_problem(problem: Problem) -> dict[str, object]:
    return {
        **serialize_problem_summary(problem),
        "statement": problem.statement,
        "input_specification": problem.input_specification,
        "output_specification": problem.output_specification,
        "notes": problem.notes,
        "sample_input": problem.sample_input,
        "sample_output": problem.sample_output,
        "contest": serialize_contest_summary(problem.contest),
    }


def serialize_test_case_summary(test_case: TestCase) -> dict[str, object]:
    return {
        "id": str(test_case.id),
        "problem_id": str(test_case.problem_id),
        "position": test_case.position,
        "is_sample": test_case.is_sample,
        "is_active": test_case.is_active,
        "created_at": _serialize_datetime(test_case.created_at),
        "updated_at": _serialize_datetime(test_case.updated_at),
    }


def serialize_test_case(test_case: TestCase) -> dict[str, object]:
    return {
        **serialize_test_case_summary(test_case),
        "input_data": test_case.input_data,
        "expected_output": test_case.expected_output,
    }


def serialize_submission_summary(submission: Submission) -> dict[str, object]:
    return {
        "id": str(submission.id),
        "language": submission.language.value,
        "status": submission.status.value,
        "verdict": submission.verdict.value,
        "passed_test_count": submission.passed_test_count,
        "total_test_count": submission.total_test_count,
        "failed_test_position": submission.failed_test_position,
        "execution_time_ms": submission.execution_time_ms,
        "created_at": _serialize_datetime(submission.created_at),
        "updated_at": _serialize_datetime(submission.updated_at),
        "judged_at": _serialize_optional_datetime(submission.judged_at),
        "problem": serialize_problem_summary(submission.problem),
        "contest": serialize_contest_summary(submission.problem.contest),
        "user": serialize_user_summary(submission.user),
    }


def serialize_submission(submission: Submission) -> dict[str, object]:
    return {
        **serialize_submission_summary(submission),
        "source_code": submission.source_code,
        "judge_log": submission.judge_log,
    }