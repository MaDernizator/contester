from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from flask import Blueprint, jsonify
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from contester.auth import admin_required
from contester.extensions import db
from contester.models.contest import Contest
from contester.models.problem import Problem, ProblemStatus
from contester.request_validation import (
    get_json_object,
    read_optional_int,
    read_optional_string,
    read_required_int,
    read_required_string,
)
from contester.serializers import serialize_problem, serialize_problem_summary
from contester.services.positioning import (
    assign_problem_insert_position,
    move_problem_to_position,
)

admin_problems_blueprint = Blueprint("admin_problems", __name__)


def _read_problem_status(payload: dict[str, object], field_name: str) -> ProblemStatus:
    raw_value = read_required_string(payload, field_name, max_length=32).lower()

    try:
        return ProblemStatus(raw_value)
    except ValueError as error:
        supported = ", ".join(status.value for status in ProblemStatus)
        raise BadRequest(
            f"Field {field_name!r} must be one of: {supported}."
        ) from error


def _get_contest_or_404(contest_id: UUID) -> Contest:
    statement = select(Contest).where(Contest.id == contest_id)
    contest = db.session.scalar(statement)
    if contest is None:
        raise NotFound("Contest not found.")
    return contest


def _get_problem_or_404(problem_id: UUID) -> Problem:
    statement = (
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.id == problem_id)
    )
    problem = db.session.scalar(statement)
    if problem is None:
        raise NotFound("Problem not found.")
    return problem


def _find_problem_by_code(*, contest_id: UUID, code: str) -> Problem | None:
    normalized_code = Problem.normalize_code(code)
    statement = select(Problem).where(
        Problem.contest_id == contest_id,
        Problem.code == normalized_code,
    )
    return db.session.scalar(statement)


def _get_problem_count(contest_id: UUID) -> int:
    statement = select(func.count(Problem.id)).where(Problem.contest_id == contest_id)
    return int(db.session.scalar(statement) or 0)


@admin_problems_blueprint.get("/admin/contests/<uuid:contest_id>/problems")
@admin_required
def list_admin_problems(contest_id: UUID):
    _get_contest_or_404(contest_id)

    statement = (
        select(Problem)
        .options(selectinload(Problem.contest))
        .where(Problem.contest_id == contest_id)
        .order_by(Problem.position.asc(), Problem.id.asc())
    )
    problems = db.session.execute(statement).scalars().all()

    return (
        jsonify({"problems": [serialize_problem_summary(problem) for problem in problems]}),
        HTTPStatus.OK,
    )


@admin_problems_blueprint.post("/admin/contests/<uuid:contest_id>/problems")
@admin_required
def create_problem(contest_id: UUID):
    contest = _get_contest_or_404(contest_id)
    payload = get_json_object()

    code = read_required_string(payload, "code", max_length=32)
    title = read_required_string(payload, "title", max_length=160)
    statement_text = read_required_string(payload, "statement")
    input_specification = read_optional_string(payload, "input_specification")
    output_specification = read_optional_string(payload, "output_specification")
    notes = read_optional_string(payload, "notes")
    sample_input = read_optional_string(payload, "sample_input")
    sample_output = read_optional_string(payload, "sample_output")
    time_limit_ms = read_optional_int(payload, "time_limit_ms", min_value=100) or 2000
    memory_limit_mb = read_optional_int(payload, "memory_limit_mb", min_value=16) or 256
    requested_position = read_optional_int(payload, "position", min_value=1)
    status = (
        _read_problem_status(payload, "status")
        if "status" in payload
        else ProblemStatus.DRAFT
    )

    try:
        normalized_code = Problem.normalize_code(code)
    except ValueError as error:
        raise BadRequest(str(error)) from error

    if _find_problem_by_code(contest_id=contest.id, code=normalized_code) is not None:
        raise Conflict("Problem code already exists in this contest.")

    problem_count = _get_problem_count(contest.id)
    if requested_position is not None and requested_position > problem_count + 1:
        raise BadRequest(
            f"Field 'position' must be less than or equal to {problem_count + 1}."
        )

    try:
        position = assign_problem_insert_position(
            contest_id=contest.id,
            requested_position=requested_position,
        )

        problem = Problem.create(
            contest=contest,
            code=normalized_code,
            title=title,
            statement=statement_text,
            input_specification=input_specification,
            output_specification=output_specification,
            notes=notes,
            sample_input=sample_input,
            sample_output=sample_output,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
            position=position,
            status=status,
        )
        db.session.add(problem)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Problem with the provided code already exists in this contest.") from error

    return jsonify({"problem": serialize_problem(problem)}), HTTPStatus.CREATED


@admin_problems_blueprint.get("/admin/problems/<uuid:problem_id>")
@admin_required
def get_admin_problem(problem_id: UUID):
    problem = _get_problem_or_404(problem_id)
    return jsonify({"problem": serialize_problem(problem)}), HTTPStatus.OK


@admin_problems_blueprint.patch("/admin/problems/<uuid:problem_id>")
@admin_required
def update_admin_problem(problem_id: UUID):
    payload = get_json_object()
    problem = _get_problem_or_404(problem_id)
    contest_id = problem.contest_id

    try:
        if "code" in payload:
            normalized_code = Problem.normalize_code(
                read_required_string(payload, "code", max_length=32)
            )
            existing = _find_problem_by_code(contest_id=contest_id, code=normalized_code)
            if existing is not None and existing.id != problem.id:
                raise Conflict("Problem code already exists in this contest.")
            problem.set_code(normalized_code)

        if "title" in payload:
            problem.set_title(read_required_string(payload, "title", max_length=160))

        if "statement" in payload:
            problem.set_statement(read_required_string(payload, "statement"))

        if "input_specification" in payload:
            problem.set_input_specification(read_optional_string(payload, "input_specification"))

        if "output_specification" in payload:
            problem.set_output_specification(read_optional_string(payload, "output_specification"))

        if "notes" in payload:
            problem.set_notes(read_optional_string(payload, "notes"))

        if "sample_input" in payload:
            problem.set_sample_input(read_optional_string(payload, "sample_input"))

        if "sample_output" in payload:
            problem.set_sample_output(read_optional_string(payload, "sample_output"))

        if "time_limit_ms" in payload or "memory_limit_mb" in payload:
            time_limit_ms = (
                read_required_int(payload, "time_limit_ms", min_value=100)
                if "time_limit_ms" in payload
                else problem.time_limit_ms
            )
            memory_limit_mb = (
                read_required_int(payload, "memory_limit_mb", min_value=16)
                if "memory_limit_mb" in payload
                else problem.memory_limit_mb
            )
            problem.set_limits(
                time_limit_ms=time_limit_ms,
                memory_limit_mb=memory_limit_mb,
            )

        if "status" in payload:
            problem.set_status(_read_problem_status(payload, "status"))

        if "position" in payload:
            new_position = read_required_int(payload, "position", min_value=1)
            max_position = _get_problem_count(contest_id)
            if new_position > max_position:
                raise BadRequest(f"Field 'position' must be less than or equal to {max_position}.")
            move_problem_to_position(
                problem=problem,
                requested_position=new_position,
            )

        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Problem with the provided code already exists in this contest.") from error

    return jsonify({"problem": serialize_problem(problem)}), HTTPStatus.OK