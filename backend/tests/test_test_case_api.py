from __future__ import annotations

from http import HTTPStatus

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
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


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def test_admin_can_create_test_case(client) -> None:
    admin = _create_user(username="admin-testcase-1", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Contest",
        slug="contest-testcase-1",
        status=ContestStatus.DRAFT,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "input_data": "1 2\n",
            "expected_output": "3\n",
            "is_sample": True,
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["test_case"]["position"] == 1
    assert payload["test_case"]["is_sample"] is True
    assert payload["test_case"]["is_active"] is True


def test_admin_can_reorder_test_cases(client) -> None:
    admin = _create_user(username="admin-testcase-2", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Contest",
        slug="contest-testcase-2",
        status=ContestStatus.DRAFT,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    first = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={"input_data": "1 2\n", "expected_output": "3\n"},
    )
    second = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={"input_data": "2 5\n", "expected_output": "7\n"},
    )

    first_id = first.get_json()["test_case"]["id"]
    second_id = second.get_json()["test_case"]["id"]

    response = client.patch(
        f"/api/v1/admin/test-cases/{second_id}",
        json={"position": 1},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.get_json()["test_case"]["position"] == 1

    list_response = client.get(f"/api/v1/admin/problems/{problem.id}/test-cases")
    assert list_response.status_code == HTTPStatus.OK
    positions = [(item["id"], item["position"]) for item in list_response.get_json()["test_cases"]]
    assert positions == [(second_id, 1), (first_id, 2)]