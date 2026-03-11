from __future__ import annotations

from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from sqlalchemy import select

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
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


def _login(client, *, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == HTTPStatus.OK


def _create_contest(
    *,
    creator: User,
    title: str,
    slug: str,
    status: ContestStatus,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Contest:
    contest = Contest.create(
        title=title,
        slug=slug,
        description="Contest description",
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
        created_by=creator,
    )
    db.session.add(contest)
    db.session.commit()
    return contest


def test_admin_can_create_contest(client, app) -> None:
    admin = _create_user(username="admin1", password="verystrong123", role=UserRole.ADMIN)
    _login(client, username="admin1", password="verystrong123")

    response = client.post(
        "/api/v1/admin/contests",
        json={
            "title": "Spring Training Contest",
            "slug": "spring-training-2026",
            "description": "Introductory contest for the training camp.",
            "starts_at": "2026-03-20T10:00:00Z",
            "ends_at": "2026-03-20T15:00:00Z",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.get_json()
    assert payload is not None
    assert payload["contest"]["title"] == "Spring Training Contest"
    assert payload["contest"]["slug"] == "spring-training-2026"
    assert payload["contest"]["status"] == "draft"
    assert payload["contest"]["created_by"]["username"] == "admin1"

    with app.app_context():
        created_contest = db.session.scalar(select(Contest).where(Contest.slug == "spring-training-2026"))
        assert created_contest is not None
        assert created_contest.created_by_id == admin.id
        assert created_contest.status == ContestStatus.DRAFT


def test_participant_cannot_create_contest(client) -> None:
    _create_user(username="user1", password="verystrong123", role=UserRole.PARTICIPANT)
    _login(client, username="user1", password="verystrong123")

    response = client.post(
        "/api/v1/admin/contests",
        json={
            "title": "Forbidden Contest",
            "slug": "forbidden-contest",
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_can_publish_contest_via_patch(client, app) -> None:
    admin = _create_user(username="admin2", password="verystrong123", role=UserRole.ADMIN)
    contest = _create_contest(
        creator=admin,
        title="Autumn Contest",
        slug="autumn-contest",
        status=ContestStatus.DRAFT,
    )

    _login(client, username="admin2", password="verystrong123")

    response = client.patch(
        f"/api/v1/admin/contests/{contest.id}",
        json={
            "status": "published",
            "description": "Published version.",
        },
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert payload["contest"]["status"] == "published"
    assert payload["contest"]["description"] == "Published version."

    with app.app_context():
        updated = db.session.get(Contest, contest.id)
        assert updated is not None
        assert updated.status == ContestStatus.PUBLISHED


def test_create_contest_rejects_invalid_schedule(client) -> None:
    _create_user(username="admin3", password="verystrong123", role=UserRole.ADMIN)
    _login(client, username="admin3", password="verystrong123")

    response = client.post(
        "/api/v1/admin/contests",
        json={
            "title": "Broken Contest",
            "slug": "broken-contest",
            "starts_at": "2026-03-20T15:00:00Z",
            "ends_at": "2026-03-20T10:00:00Z",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.get_json()["error"]["code"] == "bad_request"


def test_contests_list_requires_authentication(client) -> None:
    response = client.get("/api/v1/contests")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_authenticated_user_sees_only_published_contests(client) -> None:
    admin = _create_user(username="admin4", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant1",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    now = datetime.now(timezone.utc)
    _create_contest(
        creator=admin,
        title="Visible Contest",
        slug="visible-contest",
        status=ContestStatus.PUBLISHED,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=5),
    )
    _create_contest(
        creator=admin,
        title="Hidden Draft Contest",
        slug="hidden-draft-contest",
        status=ContestStatus.DRAFT,
    )

    _login(client, username=participant.username, password="verystrong123")

    response = client.get("/api/v1/contests")

    assert response.status_code == HTTPStatus.OK
    payload = response.get_json()
    assert payload is not None
    assert len(payload["contests"]) == 1
    assert payload["contests"][0]["slug"] == "visible-contest"
    assert payload["contests"][0]["status"] == "published"


def test_participant_can_open_only_published_contest(client) -> None:
    admin = _create_user(username="admin5", password="verystrong123", role=UserRole.ADMIN)
    participant = _create_user(
        username="participant2",
        password="verystrong123",
        role=UserRole.PARTICIPANT,
    )

    _create_contest(
        creator=admin,
        title="Published Contest",
        slug="published-contest",
        status=ContestStatus.PUBLISHED,
    )
    _create_contest(
        creator=admin,
        title="Draft Contest",
        slug="draft-contest",
        status=ContestStatus.DRAFT,
    )

    _login(client, username=participant.username, password="verystrong123")

    published_response = client.get("/api/v1/contests/published-contest")
    assert published_response.status_code == HTTPStatus.OK
    assert published_response.get_json()["contest"]["slug"] == "published-contest"

    draft_response = client.get("/api/v1/contests/draft-contest")
    assert draft_response.status_code == HTTPStatus.NOT_FOUND
    assert draft_response.get_json()["error"]["code"] == "not_found"