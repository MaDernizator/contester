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


def _create_problem(*, contest: Contest, code: str, title: str, position: int, status: ProblemStatus) -> Problem:
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


def test_judge_executes_test_cases_in_final_position_order_after_rebalance(client, app) -> None:
    admin = _create_user(username="admin-ordering-1", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(username="participant-ordering-1", password="verystrong123", role=UserRole.PARTICIPANT)
    contest = _create_contest(
        creator=admin,
        title="Judge ordering contest",
        slug="judge-ordering-contest",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    _login(client, username=admin.username, password="verystrong123")
    first_response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "input_data": "\n",
            "expected_output": "second\n",
        },
    )
    assert first_response.status_code == HTTPStatus.CREATED

    second_response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "position": 1,
            "input_data": "\n",
            "expected_output": "first\n",
        },
    )
    assert second_response.status_code == HTTPStatus.CREATED
    assert second_response.get_json()["test_case"]["position"] == 1

    client.post("/api/v1/auth/logout")
    _login(client, username=participant.username, password="verystrong123")

    submit_response = client.post(
        "/api/v1/contests/judge-ordering-contest/problems/A/submissions",
        json={
            "language": "python",
            "source_code": (
                "from pathlib import Path\n"
                "state = Path('judge-order-state.txt')\n"
                "if state.exists():\n"
                "    print('second')\n"
                "else:\n"
                "    state.write_text('x', encoding='utf-8')\n"
                "    print('first')\n"
            ),
        },
    )
    assert submit_response.status_code == HTTPStatus.ACCEPTED

    processed = _process_queue(app)
    assert processed == 1

    submission_id = submit_response.get_json()["submission"]["id"]
    submission_response = client.get(f"/api/v1/submissions/{submission_id}")
    assert submission_response.status_code == HTTPStatus.OK
    payload = submission_response.get_json()
    assert payload is not None
    assert payload["submission"]["verdict"] == "accepted"
    assert payload["submission"]["passed_test_count"] == 2
    assert payload["submission"]["total_test_count"] == 2