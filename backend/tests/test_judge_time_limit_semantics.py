from __future__ import annotations

from http import HTTPStatus

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.user import User, UserRole
from contester.services import SubmissionQueueService


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
    time_limit_ms: int,
) -> Problem:
    problem = Problem.create(
        contest=contest,
        code=code,
        title=title,
        statement="Sleep for the requested amount of time and print ok.",
        input_specification="Single float value in seconds.",
        output_specification="Print ok.",
        notes=None,
        sample_input="0.1\n",
        sample_output="ok\n",
        time_limit_ms=time_limit_ms,
        memory_limit_mb=128,
        position=position,
        status=status,
    )
    db.session.add(problem)
    db.session.commit()
    return problem


def _create_test_case(
    *,
    problem: Problem,
    position: int,
    input_data: str,
    expected_output: str,
) -> None:
    test_case = problem.test_cases[0].__class__.create(
        problem=problem,
        position=position,
        input_data=input_data,
        expected_output=expected_output,
    )
    db.session.add(test_case)
    db.session.commit()


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def _process_queue(app) -> int:
    with app.app_context():
        service = SubmissionQueueService.from_app_config()
        return service.run_once()


def test_time_limit_is_applied_per_test_case_not_per_whole_submission(client, app) -> None:
    admin = _create_user(
        username="admin-time-limit-1",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    participant = _create_user(
        username="participant-time-limit-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Per-test timeout contest",
        slug="per-test-timeout-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="Per-test timeout",
        position=1,
        status=ProblemStatus.PUBLISHED,
        time_limit_ms=250,
    )

    _create_test_case(problem=problem, position=1, input_data="0.10\n", expected_output="ok\n")
    _create_test_case(problem=problem, position=2, input_data="0.10\n", expected_output="ok\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/per-test-timeout-contest/problems/A/submissions",
        json={
            "language": "python",
            "source_code": (
                "import sys\n"
                "import time\n"
                "\n"
                "delay = float(sys.stdin.read().strip())\n"
                "time.sleep(delay)\n"
                "print('ok')\n"
            ),
        },
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    payload = response.get_json()
    assert payload is not None
    submission_id = payload["submission"]["id"]
    assert payload["submission"]["status"] == "pending"
    assert payload["submission"]["verdict"] == "pending"

    processed = _process_queue(app)
    assert processed == 1

    judged_response = client.get(f"/api/v1/submissions/{submission_id}")
    assert judged_response.status_code == HTTPStatus.OK

    judged_payload = judged_response.get_json()
    assert judged_payload is not None
    assert judged_payload["submission"]["verdict"] == "accepted"
    assert judged_payload["submission"]["status"] == "finished"
    assert judged_payload["submission"]["passed_test_count"] == 2
    assert judged_payload["submission"]["total_test_count"] == 2


def test_time_limit_exceeded_reports_the_exact_failed_test_position(client, app) -> None:
    admin = _create_user(
        username="admin-time-limit-2",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    participant = _create_user(
        username="participant-time-limit-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Timeout position contest",
        slug="timeout-position-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="Timeout position",
        position=1,
        status=ProblemStatus.PUBLISHED,
        time_limit_ms=150,
    )

    _create_test_case(problem=problem, position=1, input_data="0.05\n", expected_output="ok\n")
    _create_test_case(problem=problem, position=2, input_data="0.35\n", expected_output="ok\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/timeout-position-contest/problems/A/submissions",
        json={
            "language": "python",
            "source_code": (
                "import sys\n"
                "import time\n"
                "\n"
                "delay = float(sys.stdin.read().strip())\n"
                "time.sleep(delay)\n"
                "print('ok')\n"
            ),
        },
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    payload = response.get_json()
    assert payload is not None
    submission_id = payload["submission"]["id"]

    processed = _process_queue(app)
    assert processed == 1

    judged_response = client.get(f"/api/v1/submissions/{submission_id}")
    assert judged_response.status_code == HTTPStatus.OK

    judged_payload = judged_response.get_json()
    assert judged_payload is not None
    assert judged_payload["submission"]["verdict"] == "time_limit_exceeded"
    assert judged_payload["submission"]["status"] == "finished"
    assert judged_payload["submission"]["failed_test_position"] == 2
    assert judged_payload["submission"]["passed_test_count"] == 1
    assert judged_payload["submission"]["total_test_count"] == 2