from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from contester.models.contest import Contest
from contester.models.problem import Problem
from contester.models.submission import Submission, SubmissionStatus, SubmissionVerdict
from contester.models.user import UserRole
from contester.serializers import (
    serialize_contest_summary,
    serialize_problem_summary,
    serialize_user_summary,
)


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _minutes_between(start: datetime, end: datetime) -> int:
    delta_seconds = (end - start).total_seconds()
    if delta_seconds <= 0:
        return 0
    return int(delta_seconds // 60)


@dataclass(slots=True)
class ProblemStandingCell:
    problem: Problem
    attempt_count: int
    accepted: bool
    wrong_attempts_before_accept: int
    last_verdict: SubmissionVerdict | None
    accepted_at: datetime | None
    penalty_minutes: int | None


@dataclass(slots=True)
class ContestStandingRow:
    user_id: UUID
    username: str
    user_payload: dict[str, object]
    solved_count: int
    penalty_minutes: int
    total_attempt_count: int
    last_activity_at: datetime | None
    problem_cells: dict[UUID, ProblemStandingCell]


def _build_problem_cell(
    *,
    problem: Problem,
    submissions: list[Submission],
    reference_start: datetime,
) -> ProblemStandingCell:
    sorted_submissions = sorted(
        submissions,
        key=lambda item: (
            _ensure_utc_datetime(item.created_at) or datetime.min.replace(tzinfo=timezone.utc),
            str(item.id),
        ),
    )

    accepted_submission: Submission | None = None
    considered_submissions: list[Submission] = []
    wrong_attempts_before_accept = 0

    for submission in sorted_submissions:
        considered_submissions.append(submission)

        if submission.verdict == SubmissionVerdict.ACCEPTED:
            accepted_submission = submission
            break

        wrong_attempts_before_accept += 1

    if accepted_submission is None:
        last_verdict = considered_submissions[-1].verdict if considered_submissions else None
        return ProblemStandingCell(
            problem=problem,
            attempt_count=len(considered_submissions),
            accepted=False,
            wrong_attempts_before_accept=wrong_attempts_before_accept,
            last_verdict=last_verdict,
            accepted_at=None,
            penalty_minutes=None,
        )

    accepted_at = _ensure_utc_datetime(accepted_submission.created_at)
    if accepted_at is None:
        raise ValueError("Accepted submission must have created_at value.")

    penalty_minutes = _minutes_between(reference_start, accepted_at) + (
        wrong_attempts_before_accept * 20
    )

    return ProblemStandingCell(
        problem=problem,
        attempt_count=len(considered_submissions),
        accepted=True,
        wrong_attempts_before_accept=wrong_attempts_before_accept,
        last_verdict=SubmissionVerdict.ACCEPTED,
        accepted_at=accepted_at,
        penalty_minutes=penalty_minutes,
    )


def build_contest_standings(contest: Contest) -> dict[str, Any]:
    published_problems = [
        problem
        for problem in contest.problems
        if problem.status.value == "published"
    ]

    reference_start = _ensure_utc_datetime(contest.starts_at) or _ensure_utc_datetime(contest.created_at)
    if reference_start is None:
        raise ValueError("Contest must have a valid reference datetime.")

    rows_by_user: dict[UUID, ContestStandingRow] = {}

    for problem in published_problems:
        participant_submissions: dict[UUID, list[Submission]] = {}

        for submission in problem.submissions:
            if submission.status != SubmissionStatus.FINISHED:
                continue
            if submission.user.role != UserRole.PARTICIPANT:
                continue

            participant_submissions.setdefault(submission.user_id, []).append(submission)

        for user_problem_submissions in participant_submissions.values():
            user = user_problem_submissions[0].user
            user_id = user.id

            if user_id not in rows_by_user:
                rows_by_user[user_id] = ContestStandingRow(
                    user_id=user_id,
                    username=user.username,
                    user_payload=serialize_user_summary(user),
                    solved_count=0,
                    penalty_minutes=0,
                    total_attempt_count=0,
                    last_activity_at=None,
                    problem_cells={},
                )

            cell = _build_problem_cell(
                problem=problem,
                submissions=user_problem_submissions,
                reference_start=reference_start,
            )

            row = rows_by_user[user_id]
            row.problem_cells[problem.id] = cell
            row.total_attempt_count += cell.attempt_count

            submission_times = [
                _ensure_utc_datetime(item.created_at)
                for item in user_problem_submissions
                if _ensure_utc_datetime(item.created_at) is not None
            ]
            if submission_times:
                latest_for_problem = max(submission_times)
                if row.last_activity_at is None or latest_for_problem > row.last_activity_at:
                    row.last_activity_at = latest_for_problem

            if cell.accepted:
                row.solved_count += 1
                row.penalty_minutes += cell.penalty_minutes or 0

    sorted_rows = sorted(
        rows_by_user.values(),
        key=lambda row: (
            -row.solved_count,
            row.penalty_minutes,
            row.total_attempt_count,
            row.last_activity_at or datetime.max.replace(tzinfo=timezone.utc),
            row.username,
        ),
    )

    serialized_rows: list[dict[str, object]] = []
    previous_rank_key: tuple[object, ...] | None = None
    previous_rank = 0

    for index, row in enumerate(sorted_rows, start=1):
        rank_key = (
            row.solved_count,
            row.penalty_minutes,
            row.total_attempt_count,
            row.last_activity_at,
        )

        if rank_key == previous_rank_key:
            rank = previous_rank
        else:
            rank = index
            previous_rank = rank
            previous_rank_key = rank_key

        problem_results = []
        for problem in published_problems:
            cell = row.problem_cells.get(problem.id)
            if cell is None:
                problem_results.append(
                    {
                        "problem": serialize_problem_summary(problem),
                        "attempt_count": 0,
                        "accepted": False,
                        "wrong_attempts_before_accept": 0,
                        "last_verdict": None,
                        "accepted_at": None,
                        "penalty_minutes": None,
                    }
                )
                continue

            problem_results.append(
                {
                    "problem": serialize_problem_summary(problem),
                    "attempt_count": cell.attempt_count,
                    "accepted": cell.accepted,
                    "wrong_attempts_before_accept": cell.wrong_attempts_before_accept,
                    "last_verdict": cell.last_verdict.value if cell.last_verdict is not None else None,
                    "accepted_at": _serialize_optional_datetime(cell.accepted_at),
                    "penalty_minutes": cell.penalty_minutes,
                }
            )

        serialized_rows.append(
            {
                "rank": rank,
                "user": row.user_payload,
                "solved_count": row.solved_count,
                "penalty_minutes": row.penalty_minutes,
                "total_attempt_count": row.total_attempt_count,
                "last_activity_at": _serialize_optional_datetime(row.last_activity_at),
                "problem_results": problem_results,
            }
        )

    generated_at = datetime.now(timezone.utc)

    return {
        "contest": serialize_contest_summary(contest),
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "problems": [serialize_problem_summary(problem) for problem in published_problems],
        "rows": serialized_rows,
    }