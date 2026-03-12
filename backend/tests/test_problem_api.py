from __future__ import annotations

from http import HTTPStatus

from sqlalchemy import select

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.user import User, UserRole


def _create_user(
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.PARTICIPANT,
) -> User:
    user = User.create(
        username=username,
        password=password,
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_contest(
    *,
    creator: User,
    title: str,
    slug: str,
    status: ContestStatus,
) -> Contest:
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
        time_limit_ms=2000,
        memory_limit_mb=256,
        position=position,
        status=status,
    )
    db.session.add(problem)
    db.session.commit()
    return problem


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == HTTPStatus.OK


def test_admin_can_create_problem(client, app) -> None:
    admin = _create_user(username="admin-problem-1", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Problem Contest",
        slug="problem-contest",
        status=ContestStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(
        f"/api/v1/admin/contests/{contest.id}/problems",
        json={
            "code": "a",
            "title": "A + B",
            "statement": "Calculate the sum of two integers.",
            "input_specification": "Two integers a and b.",
            "output_specification": "Print a + b.",
            "sample_input": "1 2",
            "sample_output": "3",
            "time_limit_ms": 1000,
            "memory_limit_mb": 128,
            "status": "draft",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["problem"]["code"] == "A"
    assert payload["problem"]["title"] == "A + B"
    assert payload["problem"]["position"] == 1
    assert payload["problem"]["contest"]["slug"] == "problem-contest"

    with app.app_context():
        created_problem = db.session.scalar(
            select(Problem).where(
                Problem.contest_id == contest.id,
                Problem.code == "A",
            )
        )
        assert created_problem is not None
        assert created_problem.position == 1
        assert created_problem.time_limit_ms == 1000
        assert created_problem.memory_limit_mb == 128


def test_admin_problem_codes_are_unique_within_contest(client) -> None:
    admin = _create_user(username="admin-problem-2", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Unique Code Contest",
        slug="unique-code-contest",
        status=ContestStatus.DRAFT,
    )
    _create_problem(
        contest=contest,
        code="A",
        title="First Problem",
        position=1,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(
        f"/api/v1/admin/contests/{contest.id}/problems",
        json={
            "code": "a",
            "title": "Duplicate Problem",
            "statement": "Duplicate statement.",
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.get_json()["error"]["code"] == "conflict"


def test_admin_can_reorder_problem_positions(client, app) -> None:
    admin = _create_user(username="admin-problem-3", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Reorder Contest",
        slug="reorder-contest",
        status=ContestStatus.DRAFT,
    )
    first_problem = _create_problem(
        contest=contest,
        code="A",
        title="First",
        position=1,
        status=ProblemStatus.DRAFT,
    )
    second_problem = _create_problem(
        contest=contest,
        code="B",
        title="Second",
        position=2,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.patch(
        f"/api/v1/admin/problems/{second_problem.id}",
        json={
            "position": 1,
            "status": "published",
        },
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert payload["problem"]["position"] == 1
    assert payload["problem"]["status"] == "published"

    with app.app_context():
        updated_first = db.session.get(Problem, first_problem.id)
        updated_second = db.session.get(Problem, second_problem.id)
        assert updated_first is not None
        assert updated_second is not None
        assert updated_first.position == 2
        assert updated_second.position == 1
        assert updated_second.status == ProblemStatus.PUBLISHED


def test_participant_sees_only_published_problems_of_published_contest(client) -> None:
    admin = _create_user(username="admin-problem-4", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-problem-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    published_contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="published-problem-contest",
        status=ContestStatus.PUBLISHED,
    )
    draft_contest = _create_contest(
        creator=admin,
        title="Draft Contest",
        slug="draft-problem-contest",
        status=ContestStatus.DRAFT,
    )

    _create_problem(
        contest=published_contest,
        code="A",
        title="Visible Problem",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_problem(
        contest=published_contest,
        code="B",
        title="Hidden Draft Problem",
        position=2,
        status=ProblemStatus.DRAFT,
    )
    _create_problem(
        contest=draft_contest,
        code="A",
        title="Hidden Contest Problem",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )

    _login(client, username=participant.username, password="verystrong123")

    response = client.get("/api/v1/contests/published-problem-contest/problems")

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert len(payload["problems"]) == 1
    assert payload["problems"][0]["code"] == "A"
    assert payload["problems"][0]["title"] == "Visible Problem"

    hidden_contest_response = client.get("/api/v1/contests/draft-problem-contest/problems")
    assert hidden_contest_response.status_code == HTTPStatus.NOT_FOUND


def test_participant_can_open_only_published_problem(client) -> None:
    admin = _create_user(username="admin-problem-5", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-problem-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Open Problem Contest",
        slug="open-problem-contest",
        status=ContestStatus.PUBLISHED,
    )

    _create_problem(
        contest=contest,
        code="A",
        title="Open Problem",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_problem(
        contest=contest,
        code="B",
        title="Closed Problem",
        position=2,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=participant.username, password="verystrong123")

    visible_response = client.get("/api/v1/contests/open-problem-contest/problems/a")
    assert visible_response.status_code == HTTPStatus.OK
    visible_payload = visible_response.get_json()
    assert visible_payload is not None
    assert visible_payload["problem"]["code"] == "A"
    assert visible_payload["problem"]["statement"] == "Solve the problem."

    hidden_response = client.get("/api/v1/contests/open-problem-contest/problems/b")
    assert hidden_response.status_code == HTTPStatus.NOT_FOUND
    assert hidden_response.get_json()["error"]["code"] == "not_found"