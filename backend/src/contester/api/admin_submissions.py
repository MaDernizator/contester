from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from contester.auth import admin_required
from contester.extensions import db
from contester.models.contest import Contest
from contester.models.problem import Problem
from contester.models.submission import (
    Submission,
    SubmissionLanguage,
    SubmissionStatus,
    SubmissionVerdict,
)
from contester.models.user import User
from contester.serializers import serialize_submission, serialize_submission_summary

admin_submissions_blueprint = Blueprint("admin_submissions", __name__)


def _read_optional_query_string(name: str) -> str | None:
    value = request.args.get(name)
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _read_optional_language() -> SubmissionLanguage | None:
    raw_value = _read_optional_query_string("language")
    if raw_value is None:
        return None

    try:
        return SubmissionLanguage(raw_value.lower())
    except ValueError as error:
        supported = ", ".join(item.value for item in SubmissionLanguage)
        raise BadRequest(f"Query parameter 'language' must be one of: {supported}.") from error


def _read_optional_status() -> SubmissionStatus | None:
    raw_value = _read_optional_query_string("status")
    if raw_value is None:
        return None

    try:
        return SubmissionStatus(raw_value.lower())
    except ValueError as error:
        supported = ", ".join(item.value for item in SubmissionStatus)
        raise BadRequest(f"Query parameter 'status' must be one of: {supported}.") from error


def _read_optional_verdict() -> SubmissionVerdict | None:
    raw_value = _read_optional_query_string("verdict")
    if raw_value is None:
        return None

    try:
        return SubmissionVerdict(raw_value.lower())
    except ValueError as error:
        supported = ", ".join(item.value for item in SubmissionVerdict)
        raise BadRequest(f"Query parameter 'verdict' must be one of: {supported}.") from error


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


@admin_submissions_blueprint.get("/admin/submissions")
@admin_required
def list_admin_submissions():
    contest_slug_raw = _read_optional_query_string("contest_slug")
    problem_code_raw = _read_optional_query_string("problem_code")
    username = _read_optional_query_string("username")
    language = _read_optional_language()
    status = _read_optional_status()
    verdict = _read_optional_verdict()

    statement = select(Submission).options(
        selectinload(Submission.user),
        selectinload(Submission.problem).selectinload(Problem.contest),
    )

    joined_problem = False
    joined_contest = False
    joined_user = False

    if contest_slug_raw is not None or problem_code_raw is not None:
        statement = statement.join(Submission.problem)
        joined_problem = True

    if contest_slug_raw is not None:
        try:
            normalized_slug = Contest.normalize_slug(contest_slug_raw)
        except ValueError as error:
            raise BadRequest(str(error)) from error

        statement = statement.join(Problem.contest)
        joined_contest = True
        statement = statement.where(Contest.slug == normalized_slug)

    if problem_code_raw is not None:
        try:
            normalized_problem_code = Problem.normalize_code(problem_code_raw)
        except ValueError as error:
            raise BadRequest(str(error)) from error

        if not joined_problem:
            statement = statement.join(Submission.problem)
            joined_problem = True

        statement = statement.where(Problem.code == normalized_problem_code)

    if username is not None:
        statement = statement.join(Submission.user)
        joined_user = True
        statement = statement.where(User.username == username)

    if language is not None:
        statement = statement.where(Submission.language == language)

    if status is not None:
        statement = statement.where(Submission.status == status)

    if verdict is not None:
        statement = statement.where(Submission.verdict == verdict)

    submissions = db.session.execute(
        statement.order_by(Submission.created_at.desc(), Submission.id.desc())
    ).scalars().all()

    return (
        jsonify({"submissions": [serialize_submission_summary(item) for item in submissions]}),
        HTTPStatus.OK,
    )


@admin_submissions_blueprint.post("/admin/submissions/<uuid:submission_id>/rejudge")
@admin_required
def rejudge_submission(submission_id: UUID):
    submission = _get_submission_or_404(submission_id)

    if submission.status == SubmissionStatus.RUNNING:
        raise Conflict("Cannot rejudge a submission that is currently running.")

    submission.requeue(judge_log="Submission was queued for rejudge by admin.")
    db.session.commit()

    return jsonify({"submission": serialize_submission(submission)}), HTTPStatus.ACCEPTED
