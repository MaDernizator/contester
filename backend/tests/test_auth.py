from __future__ import annotations

from http import HTTPStatus

from sqlalchemy import select

from contester.extensions import db
from contester.models.user import User, UserRole


def _create_user(
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.PARTICIPANT,
    email: str | None = None,
) -> User:
    user = User.create(
        username=username,
        password=password,
        role=role,
        email=email,
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_register_participant_creates_user(client, app) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "password": "verystrong123",
            "email": "ALICE@example.com",
            "full_name": "Alice Johnson",
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    payload = response.get_json()
    assert payload is not None
    assert payload["user"]["username"] == "alice"
    assert payload["user"]["email"] == "alice@example.com"
    assert payload["user"]["role"] == "participant"

    with app.app_context():
        created_user = db.session.scalar(select(User).where(User.username == "alice"))
        assert created_user is not None
        assert created_user.role == UserRole.PARTICIPANT
        assert created_user.check_password("verystrong123") is True


def test_register_rejects_duplicate_username(client) -> None:
    _create_user(username="bob", password="verystrong123")

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "bob",
            "password": "anotherstrong123",
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.get_json()["error"]["code"] == "conflict"


def test_login_and_me_flow(client) -> None:
    _create_user(username="charlie", password="verystrong123")

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "charlie",
            "password": "verystrong123",
        },
    )

    assert login_response.status_code == HTTPStatus.OK
    assert login_response.get_json()["user"]["username"] == "charlie"

    me_response = client.get("/api/v1/auth/me")

    assert me_response.status_code == HTTPStatus.OK
    assert me_response.get_json()["user"]["username"] == "charlie"


def test_login_rejects_invalid_credentials(client) -> None:
    _create_user(username="diana", password="verystrong123")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "diana",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_logout_invalidates_session(client) -> None:
    _create_user(username="eve", password="verystrong123")

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "eve",
            "password": "verystrong123",
        },
    )
    assert login_response.status_code == HTTPStatus.OK

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == HTTPStatus.NO_CONTENT

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == HTTPStatus.UNAUTHORIZED


def test_admin_route_rejects_participant(client) -> None:
    _create_user(username="frank", password="verystrong123", role=UserRole.PARTICIPANT)

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "frank",
            "password": "verystrong123",
        },
    )
    assert login_response.status_code == HTTPStatus.OK

    response = client.get("/api/v1/admin/session")

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_route_allows_admin(client) -> None:
    _create_user(username="grace", password="verystrong123", role=UserRole.ADMIN)

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "grace",
            "password": "verystrong123",
        },
    )
    assert login_response.status_code == HTTPStatus.OK

    response = client.get("/api/v1/admin/session")

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert payload["status"] == "ok"
    assert payload["user"]["role"] == "admin"