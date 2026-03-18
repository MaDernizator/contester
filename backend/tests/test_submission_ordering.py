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


def _create_problem(*, contest: Contest, code: str, title: str) -> Problem:
    problem = Problem.create(
        contest=contest,
        code=code,
        title=title,
        statement="Solve the problem.",
        input_specification="Input",
        output_specification="Output",
        notes=None,
        sample_input="1",
        sample_output="1",
        time_limit_ms=1000,
        memory_limit_mb=128,
        position=1,
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


def test_judge_executes_test_cases_in_position_order(client) -> None:
    admin = _create_user(
        username="admin-ordering-1",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    participant = _create_user(
        username="participant-ordering-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Judge Ordering Contest",
        slug="judge-ordering-contest",
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="Ordering Problem",
    )

    # Создаём тесты в "неудобном" порядке:
    # сначала position=2, потом position=1.
    # Решение ниже зависит от порядка запуска тестов.
    _create_test_case(problem=problem, position=2, input_data="", expected_output="2\n")
    _create_test_case(problem=problem, position=1, input_data="", expected_output="1\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/judge-ordering-contest/problems/A/submissions",
        json={
            "language": "python",
            "source_code": (
                "from pathlib import Path\n"
                "state = Path('judge-order-state.txt')\n"
                "if state.exists():\n"
                "    print('2')\n"
                "else:\n"
                "    state.write_text('x', encoding='utf-8')\n"
                "    print('1')\n"
            ),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["verdict"] == "accepted"
    assert payload["submission"]["passed_test_count"] == 2
    assert payload["submission"]["total_test_count"] == 2