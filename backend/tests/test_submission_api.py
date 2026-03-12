from __future__ import annotations

import os
import shutil
from http import HTTPStatus

import pytest

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import SubmissionVerdict
from contester.models.test_case import TestCase as ProblemTestCase
from contester.models.user import User, UserRole


def _has_cpp_compiler() -> bool:
    compiler = os.getenv("CXX_COMPILER", "g++")
    return shutil.which(compiler) is not None


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
    time_limit_ms: int = 1000,
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
) -> ProblemTestCase:
    test_case = ProblemTestCase.create(
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


def test_python_submission_is_accepted(client) -> None:
    admin = _create_user(username="admin-submission-1", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submission-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-accepted",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="1 2\n", expected_output="3\n")
    _create_test_case(problem=problem, position=2, input_data="10 5\n", expected_output="15\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/submission-contest-accepted/problems/A/submissions",
        json={
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["verdict"] == "accepted"
    assert payload["submission"]["status"] == "finished"
    assert payload["submission"]["passed_test_count"] == 2
    assert payload["submission"]["total_test_count"] == 2


def test_python_submission_gets_wrong_answer(client) -> None:
    admin = _create_user(username="admin-submission-2", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submission-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-wa",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="7 3\n", expected_output="10\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/submission-contest-wa/problems/A/submissions",
        json={
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a - b)\n",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["verdict"] == "wrong_answer"
    assert payload["submission"]["failed_test_position"] == 1


@pytest.mark.skipif(not _has_cpp_compiler(), reason="C++ compiler is not available")
def test_cpp_submission_is_accepted(client) -> None:
    admin = _create_user(username="admin-submission-cpp-1", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submission-cpp-1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-cpp-accepted",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="1 2\n", expected_output="3\n")
    _create_test_case(problem=problem, position=2, input_data="8 11\n", expected_output="19\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/submission-contest-cpp-accepted/problems/A/submissions",
        json={
            "language": "cpp",
            "source_code": (
                "#include <iostream>\n"
                "int main() {\n"
                "    long long a, b;\n"
                "    std::cin >> a >> b;\n"
                "    std::cout << (a + b) << '\\n';\n"
                "    return 0;\n"
                "}\n"
            ),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["language"] == "cpp"
    assert payload["submission"]["verdict"] == "accepted"
    assert payload["submission"]["status"] == "finished"
    assert payload["submission"]["passed_test_count"] == 2
    assert payload["submission"]["total_test_count"] == 2


@pytest.mark.skipif(not _has_cpp_compiler(), reason="C++ compiler is not available")
def test_cpp_submission_returns_compilation_error(client) -> None:
    admin = _create_user(username="admin-submission-cpp-2", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant-submission-cpp-2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-cpp-ce",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="1 2\n", expected_output="3\n")

    _login(client, username=participant.username, password="verystrong123")

    response = client.post(
        "/api/v1/contests/submission-contest-cpp-ce/problems/A/submissions",
        json={
            "language": "cpp",
            "source_code": (
                "#include <iostream>\n"
                "int main() {\n"
                "    std::cout << \"broken\" << std::endl\n"
                "    return 0;\n"
                "}\n"
            ),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["submission"]["language"] == "cpp"
    assert payload["submission"]["verdict"] == SubmissionVerdict.COMPILATION_ERROR.value
    assert payload["submission"]["status"] == "finished"
    assert payload["submission"]["passed_test_count"] == 0
    assert payload["submission"]["judge_log"]


def test_submission_detail_is_restricted_for_other_participants(client) -> None:
    admin = _create_user(username="admin-submission-3", password="verystrong123", role=UserRole.ADMIN)
    owner = _create_user(username="participant-owner", password="verystrong123", role=UserRole.PARTICIPANT)
    stranger = _create_user(
        username="participant-stranger",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-access",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="1 2\n", expected_output="3\n")

    _login(client, username=owner.username, password="verystrong123")
    create_response = client.post(
        "/api/v1/contests/submission-contest-access/problems/A/submissions",
        json={
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    submission_id = create_response.get_json()["submission"]["id"]

    client.post("/api/v1/auth/logout")

    _login(client, username=stranger.username, password="verystrong123")
    forbidden_response = client.get(f"/api/v1/submissions/{submission_id}")
    assert forbidden_response.status_code == HTTPStatus.FORBIDDEN

    client.post("/api/v1/auth/logout")

    _login(client, username=admin.username, password="verystrong123")
    admin_response = client.get(f"/api/v1/submissions/{submission_id}")
    assert admin_response.status_code == HTTPStatus.OK
    assert admin_response.get_json()["submission"]["user"]["username"] == owner.username


def test_list_submissions_returns_only_current_user_items(client) -> None:
    admin = _create_user(username="admin-submission-4", password="verystrong123", role=UserRole.ADMIN)
    first = _create_user(username="participant-first", password="verystrong123", role=UserRole.PARTICIPANT)
    second = _create_user(username="participant-second", password="verystrong123", role=UserRole.PARTICIPANT)

    contest = _create_contest(
        creator=admin,
        title="Published Contest",
        slug="submission-contest-list",
        status=ContestStatus.PUBLISHED,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A + B",
        position=1,
        status=ProblemStatus.PUBLISHED,
    )
    _create_test_case(problem=problem, position=1, input_data="1 2\n", expected_output="3\n")

    _login(client, username=first.username, password="verystrong123")
    first_submit = client.post(
        "/api/v1/contests/submission-contest-list/problems/A/submissions",
        json={
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        },
    )
    assert first_submit.status_code == HTTPStatus.CREATED
    client.post("/api/v1/auth/logout")

    _login(client, username=second.username, password="verystrong123")
    second_submit = client.post(
        "/api/v1/contests/submission-contest-list/problems/A/submissions",
        json={
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        },
    )
    assert second_submit.status_code == HTTPStatus.CREATED

    list_response = client.get("/api/v1/submissions")
    assert list_response.status_code == HTTPStatus.OK

    payload = list_response.get_json()
    assert payload is not None
    assert len(payload["submissions"]) == 1
    assert payload["submissions"][0]["problem"]["code"] == "A"