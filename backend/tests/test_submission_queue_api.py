from __future__ import annotations

from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import (
    Submission,
    SubmissionLanguage,
    SubmissionStatus,
    SubmissionVerdict,
)
from contester.models.user import User, UserRole


def _create_user(*, username: str, password: str, role: UserRole) -> User:
    user = User.create(username=username, password=password, role=role)
    db.session.add(user)
    db.session.commit()
    return user


def _create_contest(*, creator: User, title: str, slug: str, status: ContestStatus) -> Contest:
    contest = Contest.create(
        title=title,
        slug=slug,
        description="Contest description",
        starts_at=None,
        ends_at=None,
        status=status,
        created_by=creator,
    )
    db.session.add(contest)
    db.session.commit()
    return contest


def _create_problem(
    *,
    contest: Contest,
    code: str,
    title: str,
    position: int,
    status: ProblemStatus,
) -> Problem:
    problem = Problem.create(
        contest=contest,
        code=code,
        title=title,
        statement="Solve the problem.",
        input_specification="Input spec",
        output_specification="Output spec",
        notes=None,
        sample_input="1 2",
        sample_output="3",
        time_limit_ms=1000,
        memory_limit_mb=128,
        position=position,
        status=status,
    )
    db.session.add(problem)
    db.session.commit()
    return problem


def _create_submission(
    *,
    user: User,
    problem: Problem,
    status: SubmissionStatus,
    verdict: SubmissionVerdict,
    created_at: datetime,
) -> Submission:
    submission = Submission.create(
        user=user,
        problem=problem,
        language=SubmissionLanguage.PYTHON,
        source_code="print('ok')\n",
    )
    db.session.add(submission)
    db.session.flush()

    submission.created_at = created_at
    submission.updated_at = created_at
    submission.status = status
    submission.verdict = verdict

    if status == SubmissionStatus.FINISHED:
        submission.passed_test_count = 1 if verdict == SubmissionVerdict.ACCEPTED else 0
        submission.total_test_count = 1
        submission.judged_at = created_at
    else:
        submission.passed_test_count = 0
        submission.total_test_count = 0
        submission.judged_at = None

    db.session.commit()
    return submission


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def test_queue_monitoring_requires_authentication(client) -> None:
    response = client.get("/api/v1/admin/submissions/queue")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_queue_monitoring_rejects_participant(client) -> None:
    participant = _create_user(
        username="participant-queue-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )
    _login(client, username=participant.username, password="verystrong123")

    response = client.get("/api/v1/admin/submissions/queue")

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_queue_monitoring_returns_correct_counts(client) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = _create_user(username="admin-queue-1", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-queue-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Queue Contest",
        slug="queue-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    oldest_pending = _create_submission(
        user=participant,
        problem=problem,
        status=SubmissionStatus.PENDING,
        verdict=SubmissionVerdict.PENDING,
        created_at=now,
    )
    _create_submission(
        user=participant,
        problem=problem,
        status=SubmissionStatus.PENDING,
        verdict=SubmissionVerdict.PENDING,
        created_at=now + timedelta(minutes=1),
    )
    _create_submission(
        user=participant,
        problem=problem,
        status=SubmissionStatus.RUNNING,
        verdict=SubmissionVerdict.PENDING,
        created_at=now + timedelta(minutes=2),
    )
    _create_submission(
        user=participant,
        problem=problem,
        status=SubmissionStatus.FINISHED,
        verdict=SubmissionVerdict.ACCEPTED,
        created_at=now + timedelta(minutes=3),
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.get("/api/v1/admin/submissions/queue")

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None

    queue = payload["queue"]
    assert queue["pending_count"] == 2
    assert queue["running_count"] == 1
    assert queue["finished_count"] == 1
    assert queue["oldest_pending_submission_id"] == str(oldest_pending.id)
    assert queue["oldest_pending_created_at"].endswith("Z")