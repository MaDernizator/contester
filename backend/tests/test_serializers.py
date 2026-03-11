from __future__ import annotations

from datetime import datetime, timedelta, timezone

from contester.models.contest import Contest, ContestStatus
from contester.models.user import User, UserRole
from contester.serializers import serialize_contest


def test_serialize_contest_handles_naive_datetimes_from_database() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    admin = User.create(
        username="admin-serializer",
        password="verystrong123",
        role=UserRole.ADMIN,
    )
    admin.created_at = now
    admin.updated_at = now

    contest = Contest.create(
        title="Serializer Contest",
        slug="serializer-contest",
        description="Regression test",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        status=ContestStatus.PUBLISHED,
        created_by=admin,
    )

    contest.created_at = now
    contest.updated_at = now

    contest.starts_at = contest.starts_at.replace(tzinfo=None)
    contest.ends_at = contest.ends_at.replace(tzinfo=None)
    contest.created_at = contest.created_at.replace(tzinfo=None)
    contest.updated_at = contest.updated_at.replace(tzinfo=None)

    payload = serialize_contest(contest)

    assert payload["starts_at"].endswith("Z")
    assert payload["ends_at"].endswith("Z")
    assert payload["created_at"].endswith("Z")
    assert payload["updated_at"].endswith("Z")
    assert payload["phase"] == "upcoming"