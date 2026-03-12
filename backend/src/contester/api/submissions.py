from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from contester.auth import get_authenticated_user
from contester.extensions import db
from contester.judging import JudgeService
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import Submission, SubmissionLanguage
from contester.models.user import User, UserRole
from contester.request_validation import get_json_object, read_required_string
from contester.serializers import serialize_submission, serialize_submission_summary

submissions_blueprint = Blueprint("submissions", __name__)


def _get_published_problem_or_404(contest_slug: str, problem_code: str) -> Problem:
    normalized_slug = Contest.normalize_slug(contest_slug)
    normalized_code = Problem.normalize_code(problem_code)

    statement = (
        select(Problem)
        .options(
            selectinload(Problem.contest),
            selectinload(Problem.submissions),
        )
        .join(Problem.contest)
        .where(
            Contest.slug == normalized_slug,
            Contest.status == ContestStatus.PUBLISHED,
            Problem.code == normalized_code,
            Problem.status == ProblemStatus.PUBLISHED,
        )
    )
    problem = db.session.scalar(statement)

    if problem is None:
        raise NotFound("Problem not found.")

    return problem


def _get_submission_or_404(submission_id: UUID) -> Submission:
    statement = (
        select(Submission)
        .options(
            selectinload(Submission.user),
            selectinload(Submission.problem).selectinload(Problem.contest),
        )
        .where(Submission.id == submission_id)
    )
    submission = db.session.scalar(statement)

    if submission is None:
        raise NotFound("Submission not found.")

    return submission


def _ensure_submission_access(submission: Submission, user: User) -> None:
    if submission.user_id == user.id:
        return

    if user.role == UserRole.ADMIN:
        return

    raise Forbidden("You do not have permission to access this submission.")


def _read_submission_language(payload: dict[str, object]) -> SubmissionLanguage:
    raw_value = read_required_string(payload, "language", max_length=32).lower()

    try:
        return SubmissionLanguage(raw_value)
    except ValueError as error:
        supported = ", ".join(language.value for language in SubmissionLanguage)
        raise BadRequest(
            f"Field 'language' must be one of: {supported}."
        ) from error


@submissions_blueprint.post("/contests/<string:contest_slug>/problems/<string:problem_code>/submissions")
@login_required
def create_submission(contest_slug: str, problem_code: str):
    payload = get_json_object()
    user = get_authenticated_user()
    problem = _get_published_problem_or_404(contest_slug, problem_code)

    language = _read_submission_language(payload)
    source_code = read_required_string(
        payload,
        "source_code",
        max_length=current_app.config["MAX_SOURCE_CODE_LENGTH"],
    )

    try:
        submission = Submission.create(
            user=user,
            problem=problem,
            language=language,
            source_code=source_code,
        )
        db.session.add(submission)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error

    judge_service = JudgeService(Path(current_app.config["JUDGE_WORKSPACE_DIR"]))
    judge_service.judge_submission(submission.id)

    refreshed_submission = _get_submission_or_404(submission.id)
    return jsonify({"submission": serialize_submission(refreshed_submission)}), HTTPStatus.CREATED


@submissions_blueprint.get("/submissions")
@login_required
def list_my_submissions():
    user = get_authenticated_user()

    statement = (
        select(Submission)
        .options(
            selectinload(Submission.problem).selectinload(Problem.contest),
            selectinload(Submission.user),
        )
        .where(Submission.user_id == user.id)
        .order_by(Submission.created_at.desc())
    )
    submissions = db.session.execute(statement).scalars().all()

    return jsonify({"submissions": [serialize_submission_summary(item) for item in submissions]}), HTTPStatus.OK


@submissions_blueprint.get("/submissions/<uuid:submission_id>")
@login_required
def get_submission(submission_id: UUID):
    user = current_user
    submission = _get_submission_or_404(submission_id)
    _ensure_submission_access(submission, user)

    return jsonify({"submission": serialize_submission(submission)}), HTTPStatus.OK