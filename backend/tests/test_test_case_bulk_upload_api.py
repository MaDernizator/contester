from __future__ import annotations

import io
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


def test_admin_can_bulk_upload_paired_test_case_files(client) -> None:
    admin = _create_user(
        username="admin-upload-tests-1",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Upload tests contest",
        slug="upload-tests-contest",
        status=ContestStatus.DRAFT,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A",
        position=1,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases/upload",
        data={
            "files": [
                (io.BytesIO(b"1 2\n"), "01.in"),
                (io.BytesIO(b"3\n"), "01.out"),
                (io.BytesIO(b"5 7\n"), "02.in"),
                (io.BytesIO(b"12\n"), "02.out"),
            ]
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert len(payload["test_cases"]) == 2
    assert [item["position"] for item in payload["test_cases"]] == [1, 2]

    list_response = client.get(f"/api/v1/admin/problems/{problem.id}/test-cases")
    assert list_response.status_code == HTTPStatus.OK
    list_payload = list_response.get_json()
    assert list_payload is not None
    assert len(list_payload["test_cases"]) == 2
    assert [item["position"] for item in list_payload["test_cases"]] == [1, 2]

    first_test_case_id = payload["test_cases"][0]["id"]
    detail_response = client.get(f"/api/v1/admin/test-cases/{first_test_case_id}")
    assert detail_response.status_code == HTTPStatus.OK
    detail_payload = detail_response.get_json()
    assert detail_payload is not None
    assert detail_payload["test_case"]["is_sample"] is False
    assert detail_payload["test_case"]["is_active"] is True
    assert detail_payload["test_case"]["input_data"] == "1 2\n"
    assert detail_payload["test_case"]["expected_output"] == "3\n"


def test_bulk_upload_requires_complete_in_out_pairs(client) -> None:
    admin = _create_user(
        username="admin-upload-tests-2",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    contest = _create_contest(
        creator=admin,
        title="Upload tests invalid contest",
        slug="upload-tests-invalid-contest",
        status=ContestStatus.DRAFT,
    )
    problem = _create_problem(
        contest=contest,
        code="A",
        title="A",
        position=1,
        status=ProblemStatus.DRAFT,
    )

    _login(client, username=admin.username, password="verystrong123")

    response = client.post(
        f"/api/v1/admin/problems/{problem.id}/test-cases/upload",
        data={
            "files": [
                (io.BytesIO(b"1 2\n"), "01.in"),
                (io.BytesIO(b"5 7\n"), "02.in"),
                (io.BytesIO(b"12\n"), "02.out"),
            ]
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST