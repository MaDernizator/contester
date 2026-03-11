from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import NotFound

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.serializers import serialize_contest

contests_blueprint = Blueprint("contests", __name__)


@contests_blueprint.get("/contests")
@login_required
def list_published_contests():
    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.status == ContestStatus.PUBLISHED)
        .order_by(
            Contest.starts_at.is_(None).asc(),
            Contest.starts_at.asc(),
            Contest.created_at.desc(),
        )
    )
    contests = db.session.execute(statement).scalars().all()

    return jsonify({"contests": [serialize_contest(contest) for contest in contests]}), HTTPStatus.OK


@contests_blueprint.get("/contests/<string:slug>")
@login_required
def get_published_contest(slug: str):
    normalized_slug = Contest.normalize_slug(slug)

    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(
            Contest.slug == normalized_slug,
            Contest.status == ContestStatus.PUBLISHED,
        )
    )
    contest = db.session.scalar(statement)

    if contest is None:
        raise NotFound("Contest not found.")

    return jsonify({"contest": serialize_contest(contest)}), HTTPStatus.OK