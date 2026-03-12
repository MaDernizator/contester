from __future__ import annotations

from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import Submission, SubmissionLanguage, SubmissionVerdict
from contester.models.user import User, UserRole


def _create_user(*, username: str, password: str, role: UserRole) -> User:
    user = User.create(username=username, password=password, role=role)
    db.session.add(user)
    db.session.commit()
    return user


def _create_contest(
    *,
    creator: User,
    title: str,
    slug: str,
    status: ContestStatus,
    starts_at: datetime | None = None,
) -> Contest:
    contest = Contest.create(
        title=title,
        slug=slug,
        description="Contest description",
        starts_at=starts_at,
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


def _create_finished_submission(
    *,
    user: User,
    problem: Problem,
    verdict: SubmissionVerdict,
    submitted_at: datetime,
) -> Submission:
    submission = Submission.create(
        user=user,
        problem=problem,
        language=SubmissionLanguage.PYTHON,
        source_code="print('ok')\n",
    )
    db.session.add(submission)
    db.session.flush()

    submission.created_at = submitted_at
    submission.updated_at = submitted_at

    submission.finish(
        verdict=verdict,
        passed_test_count=1 if verdict == SubmissionVerdict.ACCEPTED else 0,
        total_test_count=1,
        failed_test_position=None if verdict == SubmissionVerdict.ACCEPTED else 1,
        execution_time_ms=10,
        judge_log=verdict.value,
    )
    submission.created_at = submitted_at
    submission.updated_at = submitted_at
    submission.judged_at = submitted_at

    db.session.commit()
    return submission


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def test_standings_requires_authentication(client) -> None:
    response = client.get("/api/v1/contests/some-contest/standings")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_standings_returns_ranked_rows_for_published_contest(client) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = _create_user(username="admin-standings-1", password="verystrong123", role=UserRole.ADMIN)
    first = _create_user(username="alice", password="verystrong123", role=UserRole.PARTICIPANT)
    second = _create_user(username="bob", password="verystrong123", role=UserRole.PARTICIPANT)

    contest = _create_contest(
        creator=admin,
        title="Standings Contest",
        slug="standings-contest",
        status=ContestStatus.PUBLISHED,
        starts_at=now,
    )

    problem_a = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    problem_b = _create_problem(
        contest=contest,
        code="B",
        title="Max",
        position=2,
        status=ProblemStatus.PUBLISHED,
    )
    _create_problem(
        contest=contest,
        code="C",
        title="Draft Problem",
        position=3,
        status=ProblemStatus.DRAFT,
    )

    _create_finished_submission(
        user=first,
        problem=problem_a,
        verdict=SubmissionVerdict.WRONG_ANSWER,
        submitted_at=now + timedelta(minutes=10),
    )
    _create_finished_submission(
        user=first,
        problem=problem_a,
        verdict=SubmissionVerdict.ACCEPTED,
        submitted_at=now + timedelta(minutes=30),
    )
    _create_finished_submission(
        user=first,
        problem=problem_b,
        verdict=SubmissionVerdict.ACCEPTED,
        submitted_at=now + timedelta(minutes=50),
    )

    _create_finished_submission(
        user=second,
        problem=problem_a,
        verdict=SubmissionVerdict.ACCEPTED,
        submitted_at=now + timedelta(minutes=20),
    )
    _create_finished_submission(
        user=second,
        problem=problem_b,
        verdict=SubmissionVerdict.WRONG_ANSWER,
        submitted_at=now + timedelta(minutes=40),
    )

    _login(client, username=first.username, password="verystrong123")

    response = client.get("/api/v1/contests/standings-contest/standings")

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None

    assert payload["contest"]["slug"] == "standings-contest"
    assert len(payload["problems"]) == 2
    assert [problem["code"] for problem in payload["problems"]] == ["A", "B"]

    rows = payload["rows"]
    assert len(rows) == 2

    first_row = rows[0]
    second_row = rows[1]

    assert first_row["rank"] == 1
    assert first_row["user"]["username"] == "alice"
    assert first_row["solved_count"] == 2
    assert first_row["penalty_minutes"] == 100
    assert first_row["total_attempt_count"] == 3

    first_problem_a = first_row["problem_results"][0]
    first_problem_b = first_row["problem_results"][1]

    assert first_problem_a["problem"]["code"] == "A"
    assert first_problem_a["accepted"] is True
    assert first_problem_a["attempt_count"] == 2
    assert first_problem_a["wrong_attempts_before_accept"] == 1
    assert first_problem_a["penalty_minutes"] == 50

    assert first_problem_b["problem"]["code"] == "B"
    assert first_problem_b["accepted"] is True
    assert first_problem_b["attempt_count"] == 1
    assert first_problem_b["wrong_attempts_before_accept"] == 0
    assert first_problem_b["penalty_minutes"] == 50

    assert second_row["rank"] == 2
    assert second_row["user"]["username"] == "bob"
    assert second_row["solved_count"] == 1
    assert second_row["penalty_minutes"] == 20
    assert second_row["total_attempt_count"] == 2

    second_problem_a = second_row["problem_results"][0]
    second_problem_b = second_row["problem_results"][1]

    assert second_problem_a["accepted"] is True
    assert second_problem_a["penalty_minutes"] == 20
    assert second_problem_b["accepted"] is False
    assert second_problem_b["attempt_count"] == 1
    assert second_problem_b["last_verdict"] == "wrong_answer"
    assert second_problem_b["penalty_minutes"] is None


def test_standings_returns_not_found_for_non_published_contest(client) -> None:
    admin = _create_user(username="admin-standings-2", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-standings-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    _create_contest(
        creator=admin,
        title="Draft Contest",
        slug="draft-standings-contest",
        status=ContestStatus.DRAFT,
    )

    _login(client, username=participant.username, password="verystrong123")

    response = client.get("/api/v1/contests/draft-standings-contest/standings")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.get_json()["error"]["code"] == "not_found"