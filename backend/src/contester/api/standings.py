from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import NotFound

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem
from contester.models.submission import Submission
from contester.standings import build_contest_standings

standings_blueprint = Blueprint("standings", __name__)


@standings_blueprint.get("/contests/<string:contest_slug>/standings")
@login_required
def get_contest_standings(contest_slug: str):
    normalized_slug = Contest.normalize_slug(contest_slug)

    statement = (
        select(Contest)
        .options(
            selectinload(Contest.problems)
            .selectinload(Problem.submissions)
            .selectinload(Submission.user),
        )
        .where(
            Contest.slug == normalized_slug,
            Contest.status == ContestStatus.PUBLISHED,
        )
    )
    contest = db.session.scalar(statement)

    if contest is None:
        raise NotFound("Contest not found.")

    payload = build_contest_standings(contest)
    return jsonify(payload), HTTPStatus.OK