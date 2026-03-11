from __future__ import annotations

from datetime import datetime, timezone

from contester.models.contest import Contest
from contester.models.user import User


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _serialize_datetime(value)


def _get_contest_phase(contest: Contest) -> str:
    now = datetime.now(timezone.utc)

    if contest.ends_at is not None and now >= contest.ends_at:
        return "finished"

    if contest.starts_at is not None and now < contest.starts_at:
        return "upcoming"

    if contest.starts_at is not None and (
        contest.ends_at is None or contest.starts_at <= now < contest.ends_at
    ):
        return "running"

    return "unscheduled"


def serialize_user(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": _serialize_datetime(user.created_at),
        "updated_at": _serialize_datetime(user.updated_at),
    }


def serialize_user_summary(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
    }


def serialize_contest(contest: Contest) -> dict[str, object]:
    return {
        "id": str(contest.id),
        "title": contest.title,
        "slug": contest.slug,
        "description": contest.description,
        "status": contest.status.value,
        "starts_at": _serialize_optional_datetime(contest.starts_at),
        "ends_at": _serialize_optional_datetime(contest.ends_at),
        "phase": _get_contest_phase(contest),
        "created_at": _serialize_datetime(contest.created_at),
        "updated_at": _serialize_datetime(contest.updated_at),
        "created_by": serialize_user_summary(contest.created_by),
    }