from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, NotFound

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.serializers import serialize_problem, serialize_problem_summary

problems_blueprint = Blueprint("problems", __name__)


def _get_published_contest_or_404(contest_slug: str) -> Contest:
    normalized_slug = Contest.normalize_slug(contest_slug)
    statement = select(Contest).where(
        Contest.slug == normalized_slug,
        Contest.status == ContestStatus.PUBLISHED,
    )
    contest = db.session.scalar(statement)
    if contest is None:
        raise NotFound("Contest not found.")
    return contest


@problems_blueprint.get("/contests/<string:contest_slug>/problems")
@login_required
def list_published_problems(contest_slug: str):
    contest = _get_published_contest_or_404(contest_slug)

    statement = (
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(
            Problem.contest_id == contest.id,
            Problem.status == ProblemStatus.PUBLISHED,
        )
        .order_by(Problem.position.asc(), Problem.created_at.asc())
    )
    problems = db.session.execute(statement).scalars().all()

    return (
        jsonify({"problems": [serialize_problem_summary(problem) for problem in problems]}),
        HTTPStatus.OK,
    )


@problems_blueprint.get("/contests/<string:contest_slug>/problems/<string:problem_code>")
@login_required
def get_published_problem(contest_slug: str, problem_code: str):
    contest = _get_published_contest_or_404(contest_slug)

    try:
        normalized_code = Problem.normalize_code(problem_code)
    except ValueError as error:
        raise BadRequest(str(error)) from error

    statement = (
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(
            Problem.contest_id == contest.id,
            Problem.code == normalized_code,
            Problem.status == ProblemStatus.PUBLISHED,
        )
    )
    problem = db.session.scalar(statement)

    if problem is None:
        raise NotFound("Problem not found.")

    return jsonify({"problem": serialize_problem(problem)}), HTTPStatus.OK