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


def _create_contest(*, creator: User, title: str, slug: str) -> Contest:
    contest = Contest.create(
        title=title,
        slug=slug,
        description="Contest description",
        starts_at=None,
        ends_at=None,
        status=ContestStatus.PUBLISHED,
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
) -> Problem:
    problem = Problem.create(
        contest=contest,
        code=code,
        title=title,
        statement="Solve the problem.",
        input_specification="Input",
        output_specification="Output",
        notes=None,
        sample_input="1 2",
        sample_output="3",
        time_limit_ms=1000,
        memory_limit_mb=128,
        position=position,
        status=ProblemStatus.PUBLISHED,
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
) -> TestCase:
    test_case = TestCase.create(
        problem=problem,
        position=position,
        input_data=input_data,
        expected_output=expected_output,
        is_sample=False,
        is_active=True,
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


def test_admin_problem_create_without_position_appends_and_list_is_sorted(client) -> None:
    admin = _create_user(
        username="admin-problem-pos-1",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Contest One",
        slug="contest-one",
    )

    _create_problem(contest=contest, code="A", title="A", position=1)
    _create_problem(contest=contest, code="B", title="B", position=2)

    _login(client, username=admin.username, password="verystrong123")

    create_response = client.post(
        f"/api/v1/admin/contests/{contest.id}/problems",
        json={
            "code": "C",
            "title": "C",
            "statement": "Statement",
            "input_specification": "Input",
            "output_specification": "Output",
            "notes": None,
            "sample_input": "1",
            "sample_output": "1",
            "time_limit_ms": 1000,
            "memory_limit_mb": 128,
            "status": "published",
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    assert create_response.get_json()["problem"]["position"] == 3

    admin_list_response = client.get(f"/api/v1/admin/contests/{contest.id}/problems")
    assert admin_list_response.status_code == HTTPStatus.OK
    admin_payload = admin_list_response.get_json()
    assert [item["code"] for item in admin_payload["problems"]] == ["A", "B", "C"]
    assert [item["position"] for item in admin_payload["problems"]] == [1, 2, 3]

    public_list_response = client.get("/api/v1/contests/contest-one/problems")
    assert public_list_response.status_code == HTTPStatus.OK
    public_payload = public_list_response.get_json()
    assert [item["code"] for item in public_payload["problems"]] == ["A", "B", "C"]


def test_admin_problem_insert_at_position_shifts_existing_items(client) -> None:
    admin = _create_user(
        username="admin-problem-pos-2",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Contest Two",
        slug="contest-two",
    )

    _create_problem(contest=contest, code="A", title="A", position=1)
    _create_problem(contest=contest, code="C", title="C", position=2)

    _login(client, username=admin.username, password="verystrong123")

    create_response = client.post(
        f"/api/v1/admin/contests/{contest.id}/problems",
        json={
            "code": "B",
            "title": "B",
            "statement": "Statement",
            "input_specification": "Input",
            "output_specification": "Output",
            "notes": None,
            "sample_input": "1",
            "sample_output": "1",
            "time_limit_ms": 1000,
            "memory_limit_mb": 128,
            "position": 2,
            "status": "published",
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    assert create_response.get_json()["problem"]["position"] == 2

    list_response = client.get(f"/api/v1/admin/contests/{contest.id}/problems")
    payload = list_response.get_json()
    assert [item["code"] for item in payload["problems"]] == ["A", "B", "C"]
    assert [item["position"] for item in payload["problems"]] == [1, 2, 3]


def test_admin_problem_update_rebalances_positions(client) -> None:
    admin = _create_user(
        username="admin-problem-pos-3",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Contest Three",
        slug="contest-three",
    )

    problem_a = _create_problem(contest=contest, code="A", title="A", position=1)
    problem_b = _create_problem(contest=contest, code="B", title="B", position=2)
    problem_c = _create_problem(contest=contest, code="C", title="C", position=3)

    _login(client, username=admin.username, password="verystrong123")

    update_response = client.patch(
        f"/api/v1/admin/problems/{problem_c.id}",
        json={
            "code": "C",
            "title": "C updated",
            "statement": "Statement",
            "input_specification": "Input",
            "output_specification": "Output",
            "notes": None,
            "sample_input": "1",
            "sample_output": "1",
            "time_limit_ms": 1000,
            "memory_limit_mb": 128,
            "position": 1,
            "status": "published",
        },
    )
    assert update_response.status_code == HTTPStatus.OK

    list_response = client.get(f"/api/v1/admin/contests/{contest.id}/problems")
    payload = list_response.get_json()
    assert [item["code"] for item in payload["problems"]] == ["C", "A", "B"]
    assert [item["position"] for item in payload["problems"]] == [1, 2, 3]

    with client.application.app_context():
        refreshed_a = db.session.get(Problem, problem_a.id)
        refreshed_b = db.session.get(Problem, problem_b.id)
        refreshed_c = db.session.get(Problem, problem_c.id)
        assert refreshed_c.position == 1
        assert refreshed_a.position == 2
        assert refreshed_b.position == 3


def test_admin_test_case_create_auto_position_and_shift(client) -> None:
    admin = _create_user(
        username="admin-test-pos-1",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Contest Four",
        slug="contest-four",
    )
    problem = _create_problem(contest=contest, code="A", title="A", position=1)

    _create_test_case(problem=problem, position=1, input_data="1\n", expected_output="1\n")

    _login(client, username=admin.username, password="verystrong123")

    append_response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "input_data": "2\n",
            "expected_output": "2\n",
            "is_sample": False,
            "is_active": True,
        },
    )
    assert append_response.status_code == HTTPStatus.CREATED
    assert append_response.get_json()["test_case"]["position"] == 2

    insert_response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases",
        json={
            "position": 1,
            "input_data": "0\n",
            "expected_output": "0\n",
            "is_sample": True,
            "is_active": True,
        },
    )
    assert insert_response.status_code == HTTPStatus.CREATED
    assert insert_response.get_json()["test_case"]["position"] == 1

    list_response = client.get(f"/api/v1/admin/problems/{problem.id}/test-cases")
    payload = list_response.get_json()
    assert [item["position"] for item in payload["test_cases"]] == [1, 2, 3]


def test_admin_test_case_update_rebalances_positions(client) -> None:
    admin = _create_user(
        username="admin-test-pos-2",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Contest Five",
        slug="contest-five",
    )
    problem = _create_problem(contest=contest, code="A", title="A", position=1)

    first = _create_test_case(problem=problem, position=1, input_data="1\n", expected_output="1\n")
    second = _create_test_case(problem=problem, position=2, input_data="2\n", expected_output="2\n")
    third = _create_test_case(problem=problem, position=3, input_data="3\n", expected_output="3\n")

    _login(client, username=admin.username, password="verystrong123")

    update_response = client.patch(
        f"/api/v1/admin/test-cases/{third.id}",
        json={
            "position": 1,
            "input_data": "3\n",
            "expected_output": "3\n",
            "is_sample": False,
            "is_active": True,
        },
    )
    assert update_response.status_code == HTTPStatus.OK

    list_response = client.get(f"/api/v1/admin/problems/{problem.id}/test-cases")
    payload = list_response.get_json()
    assert [item["position"] for item in payload["test_cases"]] == [1, 2, 3]

    with client.application.app_context():
        refreshed_first = db.session.get(TestCase, first.id)
        refreshed_second = db.session.get(TestCase, second.id)
        refreshed_third = db.session.get(TestCase, third.id)

        assert refreshed_third.position == 1
        assert refreshed_first.position == 2
        assert refreshed_second.position == 3