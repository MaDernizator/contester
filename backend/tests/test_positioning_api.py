from __future__ import annotations

from http import HTTPStatus

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.test_case import TestCase
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


def _create_test_case(*, problem: Problem, position: int, input_data: str, expected_output: str) -> TestCase:
    test_case = TestCase.create(
        problem=problem,
        position=position,
        input_data=input_data,
        expected_output=expected_output,
    )
    db.session.add(test_case)
    db.session.commit()
    return test_case


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == HTTPStatus.OK


def test_problem_insert_at_position_shifts_and_public_order_is_stable(client) -> None:
    admin = _create_user(username="admin-position-1", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(username="participant-position-1", password="verystrong123", role=UserRole.PARTICIPANT)
    contest = _create_contest(
        creator=admin,
        title="Stable problem order",
        slug="stable-problem-order",
        status=ContestStatus.PUBLISHED,
    )
    _create_problem(contest=contest, code="A", title="A", position=1, status=ProblemStatus.PUBLISHED)
    _create_problem(contest=contest, code="C", title="C", position=2, status=ProblemStatus.PUBLISHED)

    _login(client, username=admin.username, password="verystrong123")
    response = client.post(
        f"/api/v1/admin/contests/{contest.id}/problems",
        json={
            "code": "B",
            "title": "B",
            "statement": "Statement",
            "position": 2,
            "status": "published",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.get_json()["problem"]["position"] == 2

    admin_list = client.get(f"/api/v1/admin/contests/{contest.id}/problems")
    assert admin_list.status_code == HTTPStatus.OK
    assert [item["code"] for item in admin_list.get_json()["problems"]] == ["A", "B", "C"]
    assert [item["position"] for item in admin_list.get_json()["problems"]] == [1, 2, 3]

    client.post("/api/v1/auth/logout")
    _login(client, username=participant.username, password="verystrong123")
    public_list = client.get("/api/v1/contests/stable-problem-order/problems")
    assert public_list.status_code == HTTPStatus.OK
    assert [item["code"] for item in public_list.get_json()["problems"]] == ["A", "B", "C"]


def test_test_case_create_without_position_rebalances_duplicate_existing_positions(client) -> None:
    admin = _create_user(username="admin-position-2", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Stable test order",
        slug="stable-test-order",
        status=ContestStatus.DRAFT,
    )
    problem = _create_problem(contest=contest, code="A", title="A", position=1, status=ProblemStatus.DRAFT)

    _create_test_case(problem=problem, position=1, input_data="1\n", expected_output="1\n")
    _create_test_case(problem=problem, position=1, input_data="2\n", expected_output="2\n")

    _login(client, username=admin.username, password="verystrong123")
    response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "input_data": "3\n",
            "expected_output": "3\n",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.get_json()["test_case"]["position"] == 3

    list_response = client.get(f"/api/v1/admin/problems/{problem.id}/test-cases")
    assert list_response.status_code == HTTPStatus.OK
    assert [item["position"] for item in list_response.get_json()["test_cases"]] == [1, 2, 3]