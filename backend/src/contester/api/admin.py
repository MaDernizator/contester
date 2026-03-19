from __future__ import annotations

from uuid import UUID

from contester.models.user import UserRole
from contester.serializers import serialize_user

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from contester.auth import admin_required
from contester.extensions import db
from contester.models.contest import Contest, ContestStatus
from contester.models.problem import Problem, ProblemStatus
from contester.models.submission import Submission, SubmissionStatus
from contester.models.test_case import TestCase
from contester.serializers import (
    serialize_contest,
    serialize_problem,
    serialize_problem_summary,
    serialize_submission,
    serialize_submission_summary,
    serialize_test_case,
    serialize_test_case_summary,
)
from contester.services.positioning import (
    assign_problem_insert_position,
    assign_test_case_insert_position,
    move_problem_to_position,
    move_test_case_to_position,
)

admin_blueprint = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


def _error_response(message: str, status_code: int):
    return jsonify({"error": {"message": message}}), status_code


def _parse_uuid(value: str):
    try:
        return UUID(value)
    except ValueError:
        return None


def _json_payload() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {}
    return payload


def _get_contest_or_404(contest_id: str) -> Contest | None:
    parsed = _parse_uuid(contest_id)
    if parsed is None:
        return None
    return db.session.get(Contest, parsed)


def _get_problem_or_404(problem_id: str) -> Problem | None:
    parsed = _parse_uuid(problem_id)
    if parsed is None:
        return None
    return db.session.get(Problem, parsed)


def _get_test_case_or_404(test_case_id: str) -> TestCase | None:
    parsed = _parse_uuid(test_case_id)
    if parsed is None:
        return None
    return db.session.get(TestCase, parsed)


def _get_submission_or_404(submission_id: str) -> Submission | None:
    parsed = _parse_uuid(submission_id)
    if parsed is None:
        return None
    return db.session.get(Submission, parsed)


@admin_blueprint.get("/session")
@login_required
def get_admin_session():
    if getattr(current_user, "role", None) != UserRole.ADMIN:
        return _error_response("Admin access required.", 403)

    return jsonify({"user": serialize_user(current_user)})


@admin_blueprint.get("/contests")
@login_required
@admin_required
def list_admin_contests():
    contests = db.session.execute(
        select(Contest)
        .options(selectinload(Contest.created_by))
        .order_by(Contest.created_at.desc(), Contest.id.desc())
    ).scalars().all()

    return jsonify({"contests": [serialize_contest(contest) for contest in contests]})


@admin_blueprint.post("/contests")
@login_required
@admin_required
def create_admin_contest():
    payload = _json_payload()

    required_fields = ("title", "slug", "status")
    for field in required_fields:
        if field not in payload:
            return _error_response(f"Field '{field}' is required.", 400)

    try:
        status = ContestStatus(payload["status"])
    except ValueError:
        return _error_response("Invalid contest status.", 400)

    contest = Contest.create(
        title=payload["title"],
        slug=payload["slug"],
        description=payload.get("description"),
        starts_at=payload.get("starts_at"),
        ends_at=payload.get("ends_at"),
        status=status,
        created_by=current_user,
    )
    db.session.add(contest)
    db.session.commit()

    contest = db.session.execute(
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.id == contest.id)
    ).scalar_one()

    return jsonify({"contest": serialize_contest(contest)}), 201


@admin_blueprint.patch("/contests/<contest_id>")
@login_required
@admin_required
def update_admin_contest(contest_id: str):
    contest = _get_contest_or_404(contest_id)
    if contest is None:
        return _error_response("Contest not found.", 404)

    payload = _json_payload()

    if "status" in payload:
        try:
            contest.status = ContestStatus(payload["status"])
        except ValueError:
            return _error_response("Invalid contest status.", 400)

    if "title" in payload:
        contest.title = payload["title"]
    if "slug" in payload:
        contest.slug = payload["slug"]
    if "description" in payload:
        contest.description = payload["description"]
    if "starts_at" in payload:
        contest.starts_at = payload["starts_at"]
    if "ends_at" in payload:
        contest.ends_at = payload["ends_at"]

    db.session.commit()

    contest = db.session.execute(
        select(Contest)
        .options(selectinload(Contest.created_by))
        .where(Contest.id == contest.id)
    ).scalar_one()

    return jsonify({"contest": serialize_contest(contest)})


@admin_blueprint.get("/contests/<contest_id>/problems")
@login_required
@admin_required
def list_admin_problems(contest_id: str):
    contest = _get_contest_or_404(contest_id)
    if contest is None:
        return _error_response("Contest not found.", 404)

    problems = db.session.execute(
        select(Problem)
        .where(Problem.contest_id == contest.id)
        .order_by(Problem.position.asc(), Problem.id.asc())
    ).scalars().all()

    return jsonify({"problems": [serialize_problem_summary(problem) for problem in problems]})


@admin_blueprint.post("/contests/<contest_id>/problems")
@login_required
@admin_required
def create_admin_problem(contest_id: str):
    contest = _get_contest_or_404(contest_id)
    if contest is None:
        return _error_response("Contest not found.", 404)

    payload = _json_payload()

    required_fields = (
        "code",
        "title",
        "statement",
        "time_limit_ms",
        "memory_limit_mb",
        "status",
    )
    for field in required_fields:
        if field not in payload:
            return _error_response(f"Field '{field}' is required.", 400)

    try:
        status = ProblemStatus(payload["status"])
    except ValueError:
        return _error_response("Invalid problem status.", 400)

    assigned_position = assign_problem_insert_position(
        contest_id=contest.id,
        requested_position=payload.get("position"),
    )

    problem = Problem.create(
        contest=contest,
        code=payload["code"],
        title=payload["title"],
        statement=payload["statement"],
        input_specification=payload.get("input_specification"),
        output_specification=payload.get("output_specification"),
        notes=payload.get("notes"),
        sample_input=payload.get("sample_input"),
        sample_output=payload.get("sample_output"),
        time_limit_ms=payload["time_limit_ms"],
        memory_limit_mb=payload["memory_limit_mb"],
        position=assigned_position,
        status=status,
    )
    db.session.add(problem)
    db.session.commit()

    problem = db.session.execute(
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.id == problem.id)
    ).scalar_one()

    return jsonify({"problem": serialize_problem(problem)}), 201


@admin_blueprint.get("/problems/<problem_id>")
@login_required
@admin_required
def get_admin_problem(problem_id: str):
    parsed_problem_id = _parse_uuid(problem_id)
    if parsed_problem_id is None:
        return _error_response("Problem not found.", 404)

    problem = db.session.execute(
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.id == parsed_problem_id)
    ).scalar_one_or_none()

    if problem is None:
        return _error_response("Problem not found.", 404)

    return jsonify({"problem": serialize_problem(problem)})


@admin_blueprint.patch("/problems/<problem_id>")
@login_required
@admin_required
def update_admin_problem(problem_id: str):
    parsed_problem_id = _parse_uuid(problem_id)
    if parsed_problem_id is None:
        return _error_response("Problem not found.", 404)

    problem = db.session.execute(
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.id == parsed_problem_id)
    ).scalar_one_or_none()

    if problem is None:
        return _error_response("Problem not found.", 404)

    payload = _json_payload()

    if "status" in payload:
        try:
            problem.status = ProblemStatus(payload["status"])
        except ValueError:
            return _error_response("Invalid problem status.", 400)

    if "code" in payload:
        problem.code = payload["code"]
    if "title" in payload:
        problem.title = payload["title"]
    if "statement" in payload:
        problem.statement = payload["statement"]
    if "input_specification" in payload:
        problem.input_specification = payload["input_specification"]
    if "output_specification" in payload:
        problem.output_specification = payload["output_specification"]
    if "notes" in payload:
        problem.notes = payload["notes"]
    if "sample_input" in payload:
        problem.sample_input = payload["sample_input"]
    if "sample_output" in payload:
        problem.sample_output = payload["sample_output"]
    if "time_limit_ms" in payload:
        problem.time_limit_ms = payload["time_limit_ms"]
    if "memory_limit_mb" in payload:
        problem.memory_limit_mb = payload["memory_limit_mb"]

    move_problem_to_position(
        problem=problem,
        requested_position=payload.get("position", problem.position),
    )

    db.session.commit()

    problem = db.session.execute(
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.id == problem.id)
    ).scalar_one()

    return jsonify({"problem": serialize_problem(problem)})


@admin_blueprint.get("/problems/<problem_id>/test-cases")
@login_required
@admin_required
def list_admin_test_cases(problem_id: str):
    problem = _get_problem_or_404(problem_id)
    if problem is None:
        return _error_response("Problem not found.", 404)

    test_cases = db.session.execute(
        select(TestCase)
        .where(TestCase.problem_id == problem.id)
        .order_by(TestCase.position.asc(), TestCase.id.asc())
    ).scalars().all()

    return jsonify(
        {"test_cases": [serialize_test_case_summary(test_case) for test_case in test_cases]}
    )


@admin_blueprint.post("/problems/<problem_id>/test-cases")
@login_required
@admin_required
def create_admin_test_case(problem_id: str):
    problem = _get_problem_or_404(problem_id)
    if problem is None:
        return _error_response("Problem not found.", 404)

    payload = _json_payload()

    required_fields = ("input_data", "expected_output")
    for field in required_fields:
        if field not in payload:
            return _error_response(f"Field '{field}' is required.", 400)

    assigned_position = assign_test_case_insert_position(
        problem_id=problem.id,
        requested_position=payload.get("position"),
    )

    test_case = TestCase.create(
        problem=problem,
        position=assigned_position,
        input_data=payload["input_data"],
        expected_output=payload["expected_output"],
        is_sample=payload.get("is_sample", False),
        is_active=payload.get("is_active", True),
    )
    db.session.add(test_case)
    db.session.commit()

    return jsonify({"test_case": serialize_test_case(test_case)}), 201


@admin_blueprint.get("/test-cases/<test_case_id>")
@login_required
@admin_required
def get_admin_test_case(test_case_id: str):
    test_case = _get_test_case_or_404(test_case_id)
    if test_case is None:
        return _error_response("Test case not found.", 404)

    return jsonify({"test_case": serialize_test_case(test_case)})


@admin_blueprint.patch("/test-cases/<test_case_id>")
@login_required
@admin_required
def update_admin_test_case(test_case_id: str):
    test_case = _get_test_case_or_404(test_case_id)
    if test_case is None:
        return _error_response("Test case not found.", 404)

    payload = _json_payload()

    if "input_data" in payload:
        test_case.input_data = payload["input_data"]
    if "expected_output" in payload:
        test_case.expected_output = payload["expected_output"]
    if "is_sample" in payload:
        test_case.is_sample = payload["is_sample"]
    if "is_active" in payload:
        test_case.is_active = payload["is_active"]

    move_test_case_to_position(
        test_case=test_case,
        requested_position=payload.get("position", test_case.position),
    )

    db.session.commit()

    return jsonify({"test_case": serialize_test_case(test_case)})


@admin_blueprint.get("/submissions/queue")
@login_required
@admin_required
def get_admin_submission_queue():
    pending_count = db.session.scalar(
        select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.PENDING)
    ) or 0
    running_count = db.session.scalar(
        select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.RUNNING)
    ) or 0
    finished_count = db.session.scalar(
        select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.FINISHED)
    ) or 0

    oldest_pending = db.session.execute(
        select(Submission)
        .where(Submission.status == SubmissionStatus.PENDING)
        .order_by(Submission.created_at.asc(), Submission.id.asc())
        .limit(1)
    ).scalar_one_or_none()

    return jsonify(
        {
            "queue": {
                "pending_count": pending_count,
                "running_count": running_count,
                "finished_count": finished_count,
                "oldest_pending_submission_id": (
                    str(oldest_pending.id) if oldest_pending is not None else None
                ),
                "oldest_pending_created_at": (
                    oldest_pending.created_at.isoformat().replace("+00:00", "Z")
                    if oldest_pending is not None
                    else None
                ),
            }
        }
    )


@admin_blueprint.get("/submissions")
@login_required
@admin_required
def list_admin_submissions():
    contest_slug = request.args.get("contest_slug", type=str)
    problem_code = request.args.get("problem_code", type=str)
    username = request.args.get("username", type=str)
    language = request.args.get("language", type=str)
    status = request.args.get("status", type=str)
    verdict = request.args.get("verdict", type=str)

    statement = (
        select(Submission)
        .join(Submission.problem)
        .join(Problem.contest)
        .join(Submission.user)
        .options(
            selectinload(Submission.user),
            selectinload(Submission.problem).selectinload(Problem.contest),
        )
    )

    if contest_slug:
        statement = statement.where(Contest.slug == contest_slug)
    if problem_code:
        statement = statement.where(Problem.code == problem_code)
    if username:
        from contester.models.user import User

        statement = statement.where(User.username == username)
    if language:
        statement = statement.where(Submission.language == language)
    if status:
        try:
            statement = statement.where(Submission.status == SubmissionStatus(status))
        except ValueError:
            return _error_response("Invalid submission status filter.", 400)
    if verdict:
        statement = statement.where(Submission.verdict == verdict)

    submissions = db.session.execute(
        statement.order_by(Submission.created_at.desc(), Submission.id.desc())
    ).scalars().all()

    return jsonify(
        {"submissions": [serialize_submission_summary(submission) for submission in submissions]}
    )


@admin_blueprint.post("/submissions/<submission_id>/rejudge")
@login_required
@admin_required
def rejudge_admin_submission(submission_id: str):
    parsed_submission_id = _parse_uuid(submission_id)
    if parsed_submission_id is None:
        return _error_response("Submission not found.", 404)

    submission = db.session.execute(
        select(Submission)
        .options(
            selectinload(Submission.user),
            selectinload(Submission.problem).selectinload(Problem.contest),
        )
        .where(Submission.id == parsed_submission_id)
    ).scalar_one_or_none()

    if submission is None:
        return _error_response("Submission not found.", 404)

    submission.requeue(judge_log="Submission was re-queued by admin.")
    db.session.commit()

    submission = db.session.execute(
        select(Submission)
        .options(
            selectinload(Submission.user),
            selectinload(Submission.problem).selectinload(Problem.contest),
        )
        .where(Submission.id == submission.id)
    ).scalar_one()

    return jsonify({"submission": serialize_submission(submission)})
