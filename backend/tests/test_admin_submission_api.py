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
    language: SubmissionLanguage,
    status: SubmissionStatus,
    verdict: SubmissionVerdict,
    created_at: datetime,
) -> Submission:
    submission = Submission.create(
        user=user,
        problem=problem,
        language=language,
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
        submission.failed_test_position = None if verdict == SubmissionVerdict.ACCEPTED else 1
        submission.execution_time_ms = 10
        submission.judged_at = created_at
        submission.judge_log = verdict.value
    else:
        submission.passed_test_count = 0
        submission.total_test_count = 0
        submission.failed_test_position = None
        submission.execution_time_ms = None
        submission.judged_at = None
        submission.judge_log = None

    db.session.commit()
    return submission


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def test_admin_can_list_submissions_with_filters(client) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = _create_user(username="admin-submissions-1", password="verystrong123", role=UserRole.ADMIN)
    alice = _create_user(username="alice-submissions", password="verystrong123", role=UserRole.PARTICIPANT)
    bob = _create_user(username="bob-submissions", password="verystrong123", role=UserRole.PARTICIPANT)

    first_contest = _create_contest(
        creator=admin,
        title="First Contest",
        slug="first-submissions-contest",
        status=ContestStatus.PUBLISHED,
    )
    second_contest = _create_contest(
        creator=admin,
        title="Second Contest",
        slug="second-submissions-contest",
        status=ContestStatus.PUBLISHED,
    )

    problem_a = _create_problem(
        contest=first_contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    problem_b = _create_problem(
        contest=second_contest,
        code="B",
        title="Max",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    _create_submission(
        user=alice,
        problem=problem_a,
        language=SubmissionLanguage.PYTHON,
        status=SubmissionStatus.FINISHED,
        verdict=SubmissionVerdict.ACCEPTED,
        created_at=now,
    )
    _create_submission(
        user=bob,
        problem=problem_a,
        language=SubmissionLanguage.CPP,
        status=SubmissionStatus.FINISHED,
        verdict=SubmissionVerdict.WRONG_ANSWER,
        created_at=now + timedelta(minutes=1),
    )
    _create_submission(
        user=alice,
        problem=problem_b,
        language=SubmissionLanguage.CPP,
        status=SubmissionStatus.PENDING,
        verdict=SubmissionVerdict.PENDING,
        created_at=now + timedelta(minutes=2),
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.get(
        "/api/v1/admin/submissions"
        "?contest_slug=first-submissions-contest"
        "&problem_code=A"
        "&username=alice-submissions"
        "&language=python"
        "&status=finished"
        "&verdict=accepted"
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert len(payload["submissions"]) == 1
    assert payload["submissions"][0]["user"]["username"] == "alice-submissions"
    assert payload["submissions"][0]["problem"]["code"] == "A"
    assert payload["submissions"][0]["contest"]["slug"] == "first-submissions-contest"
    assert payload["submissions"][0]["language"] == "python"
    assert payload["submissions"][0]["verdict"] == "accepted"


def test_participant_cannot_access_admin_submissions(client) -> None:
    participant = _create_user(
        username="participant-submissions-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    _login(client, username=participant.username, password="verystrong123")

    response = client.get("/api/v1/admin/submissions")
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_admin_can_rejudge_finished_submission(client) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = _create_user(username="admin-submissions-2", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submissions-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )
    contest = _create_contest(
        creator=admin,
        title="Rejudge Contest",
        slug="rejudge-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    submission = _create_submission(
        user=participant,
        problem=problem,
        language=SubmissionLanguage.PYTHON,
        status=SubmissionStatus.FINISHED,
        verdict=SubmissionVerdict.WRONG_ANSWER,
        created_at=now,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(f"/api/v1/admin/submissions/{submission.id}/rejudge")

    assert response.status_code == HTTPStatus.ACCEPTED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["status"] == "pending"
    assert payload["submission"]["verdict"] == "pending"
    assert payload["submission"]["judge_log"] == "Submission was queued for rejudge by admin."


def test_admin_cannot_rejudge_running_submission(client) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = _create_user(username="admin-submissions-3", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submissions-3",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )
    contest = _create_contest(
        creator=admin,
        title="Running Contest",
        slug="running-rejudge-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    submission = _create_submission(
        user=participant,
        problem=problem,
        language=SubmissionLanguage.PYTHON,
        status=SubmissionStatus.RUNNING,
        verdict=SubmissionVerdict.PENDING,
        created_at=now,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(f"/api/v1/admin/submissions/{submission.id}/rejudge")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.get_json()["error"]["code"] == "conflict"
