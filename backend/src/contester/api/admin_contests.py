from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from flask import Blueprint, jsonify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from contester.auth import admin_required, get_authenticated_user
from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.request_validation import (
    get_json_object,
    read_optional_datetime,
    read_optional_string,
    read_required_string,
)
from contester.serializers import serialize_contest

admin_contests_blueprint = Blueprint("admin_contests", __name__)


def _read_contest_status(payload: dict[str, object], field_name: str) -> ContestStatus:
    raw_value = read_required_string(payload, field_name, max_length=32).lower()

    try:
        return ContestStatus(raw_value)
    except ValueError as error:
        supported = ", ".join(status.value for status in ContestStatus)
        raise BadRequest(
            f"Field {field_name!r} must be one of: {supported}."
        ) from error


def _find_contest_by_slug(slug: str) -> Contest | None:
    normalized_slug = Contest.normalize_slug(slug)
    statement = select(Contest).where(Contest.slug == normalized_slug)
    return db.session.scalar(statement)


def _get_contest_or_404(contest_id: UUID) -> Contest:
    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.id == contest_id)
    )
    contest = db.session.scalar(statement)
    if contest is None:
        raise NotFound("Contest not found.")
    return contest


@admin_contests_blueprint.get("/admin/contests")
@admin_required
def list_admin_contests():
    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .order_by(Contest.created_at.desc())
    )
    contests = db.session.execute(statement).scalars().all()

    return jsonify({"contests": [serialize_contest(contest) for contest in contests]}), HTTPStatus.OK


@admin_contests_blueprint.post("/admin/contests")
@admin_required
def create_contest():
    payload = get_json_object()

    title = read_required_string(payload, "title", max_length=160)
    slug = read_required_string(payload, "slug", max_length=80)
    description = read_optional_string(payload, "description")
    starts_at = read_optional_datetime(payload, "starts_at")
    ends_at = read_optional_datetime(payload, "ends_at")
    status = (
        _read_contest_status(payload, "status")
        if "status" in payload
        else ContestStatus.DRAFT
    )

    try:
        normalized_slug = Contest.normalize_slug(slug)
    except ValueError as error:
        raise BadRequest(str(error)) from error

    if _find_contest_by_slug(normalized_slug) is not None:
        raise Conflict("Contest slug already exists.")

    try:
        contest = Contest.create(
            title=title,
            slug=normalized_slug,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
            created_by=get_authenticated_user(),
        )
        db.session.add(contest)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Contest with the provided slug already exists.") from error

    return jsonify({"contest": serialize_contest(contest)}), HTTPStatus.CREATED


@admin_contests_blueprint.get("/admin/contests/<uuid:contest_id>")
@admin_required
def get_admin_contest(contest_id: UUID):
    contest = _get_contest_or_404(contest_id)
    return jsonify({"contest": serialize_contest(contest)}), HTTPStatus.OK


@admin_contests_blueprint.patch("/admin/contests/<uuid:contest_id>")
@admin_required
def update_admin_contest(contest_id: UUID):
    payload = get_json_object()
    contest = _get_contest_or_404(contest_id)

    try:
        if "title" in payload:
            contest.set_title(read_required_string(payload, "title", max_length=160))

        if "slug" in payload:
            new_slug = Contest.normalize_slug(
                read_required_string(payload, "slug", max_length=80)
            )
            existing = _find_contest_by_slug(new_slug)
            if existing is not None and existing.id != contest.id:
                raise Conflict("Contest slug already exists.")
            contest.set_slug(new_slug)

        if "description" in payload:
            contest.set_description(read_optional_string(payload, "description"))

        if "status" in payload:
            contest.set_status(_read_contest_status(payload, "status"))

        if "starts_at" in payload or "ends_at" in payload:
            starts_at = (
                read_optional_datetime(payload, "starts_at")
                if "starts_at" in payload
                else contest.starts_at
            )
            ends_at = (
                read_optional_datetime(payload, "ends_at")
                if "ends_at" in payload
                else contest.ends_at
            )
            contest.set_schedule(starts_at=starts_at, ends_at=ends_at)

        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Contest with the provided slug already exists.") from error

    return jsonify({"contest": serialize_contest(contest)}), HTTPStatus.OK