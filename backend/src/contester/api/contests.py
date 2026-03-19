from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.user import UserRole
from contester.serializers import (
    serialize_contest,
    serialize_problem,
    serialize_problem_summary,
)

contests_blueprint = Blueprint(
    "contests_api",
    __name__,
    url_prefix="/api/v1/contests",
)


def _error_response(message: str, status_code: int):
    return jsonify({"error": {"message": message}}), status_code


def _can_view_unpublished() -> bool:
    return (
        current_user.is_authenticated
        and getattr(current_user, "role", None) == UserRole.ADMIN
    )


@contests_blueprint.route("", methods=["GET"])
@login_required
def list_contests():
    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .order_by(Contest.created_at.desc(), Contest.id.desc())
    )

    if not _can_view_unpublished():
        statement = statement.where(Contest.status == ContestStatus.PUBLISHED)

    contests = db.session.execute(statement).scalars().all()

    return jsonify({"contests": [serialize_contest(contest) for contest in contests]})


@contests_blueprint.route("/<slug>", methods=["GET"])
@login_required
def get_contest(slug: str):
    statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.slug == slug)
    )

    if not _can_view_unpublished():
        statement = statement.where(Contest.status == ContestStatus.PUBLISHED)

    contest = db.session.execute(statement).scalar_one_or_none()
    if contest is None:
        return _error_response("Contest not found.", 404)

    return jsonify({"contest": serialize_contest(contest)})


@contests_blueprint.route("/<slug>/problems", methods=["GET"])
@login_required
def list_contest_problems(slug: str):
    contest_statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.slug == slug)
    )

    if not _can_view_unpublished():
        contest_statement = contest_statement.where(
            Contest.status == ContestStatus.PUBLISHED
        )

    contest = db.session.execute(contest_statement).scalar_one_or_none()
    if contest is None:
        return _error_response("Contest not found.", 404)

    problem_statement = select(Problem).where(Problem.contest_id == contest.id)

    if not _can_view_unpublished():
        problem_statement = problem_statement.where(
            Problem.status == ProblemStatus.PUBLISHED
        )

    problems = db.session.execute(
        problem_statement.order_by(Problem.position.asc(), Problem.id.asc())
    ).scalars().all()

    return jsonify(
        {"problems": [serialize_problem_summary(problem) for problem in problems]}
    )


@contests_blueprint.route("/<slug>/problems/<problem_code>", methods=["GET"])
@login_required
def get_contest_problem(slug: str, problem_code: str):
    contest_statement = (
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.slug == slug)
    )

    if not _can_view_unpublished():
        contest_statement = contest_statement.where(
            Contest.status == ContestStatus.PUBLISHED
        )

    contest = db.session.execute(contest_statement).scalar_one_or_none()
    if contest is None:
        return _error_response("Contest not found.", 404)

    problem_statement = (
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(
            Problem.contest_id == contest.id,
            Problem.code == problem_code,
        )
    )

    if not _can_view_unpublished():
        problem_statement = problem_statement.where(
            Problem.status == ProblemStatus.PUBLISHED
        )

    problem = db.session.execute(problem_statement).scalar_one_or_none()
    if problem is None:
        return _error_response("Problem not found.", 404)

    return jsonify({"problem": serialize_problem(problem)})