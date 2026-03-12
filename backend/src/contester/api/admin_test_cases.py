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
from contester.models.problem import Problem
from contester.models.test_case import TestCase
from contester.request_validation import (
    get_json_object,
    read_optional_bool,
    read_optional_int,
    read_required_int,
    read_required_string,
)
from contester.serializers import serialize_test_case, serialize_test_case_summary

admin_test_cases_blueprint = Blueprint("admin_test_cases", __name__)


def _get_problem_or_404(problem_id: UUID) -> Problem:
    statement = select(Problem).where(Problem.id == problem_id)
    problem = db.session.scalar(statement)
    if problem is None:
        raise NotFound("Problem not found.")
    return problem


def _get_test_case_or_404(test_case_id: UUID) -> TestCase:
    statement = (
        select(TestCase)
        .options(selectinload(TestCase.problem))
        .where(TestCase.id == test_case_id)
    )
    test_case = db.session.scalar(statement)
    if test_case is None:
        raise NotFound("Test case not found.")
    return test_case


def _get_test_case_count(problem_id: UUID) -> int:
    statement = select(func.count(TestCase.id)).where(TestCase.problem_id == problem_id)
    return int(db.session.scalar(statement) or 0)


def _shift_positions_for_insert(*, problem_id: UUID, from_position: int) -> None:
    statement = (
        select(TestCase)
        .where(
            TestCase.problem_id == problem_id,
            TestCase.position >= from_position,
        )
        .order_by(TestCase.position.desc(), TestCase.created_at.desc())
    )
    test_cases = db.session.execute(statement).scalars().all()

    for test_case in test_cases:
        test_case.position += 1


def _reorder_test_case(
    *,
    problem_id: UUID,
    test_case: TestCase,
    new_position: int,
) -> None:
    old_position = test_case.position
    if new_position == old_position:
        return

    if new_position < old_position:
        statement = (
            select(TestCase)
            .where(
                TestCase.problem_id == problem_id,
                TestCase.id != test_case.id,
                TestCase.position >= new_position,
                TestCase.position < old_position,
            )
            .order_by(TestCase.position.desc(), TestCase.created_at.desc())
        )
        affected = db.session.execute(statement).scalars().all()
        for other in affected:
            other.position += 1
    else:
        statement = (
            select(TestCase)
            .where(
                TestCase.problem_id == problem_id,
                TestCase.id != test_case.id,
                TestCase.position > old_position,
                TestCase.position <= new_position,
            )
            .order_by(TestCase.position.asc(), TestCase.created_at.asc())
        )
        affected = db.session.execute(statement).scalars().all()
        for other in affected:
            other.position -= 1

    test_case.position = new_position


@admin_test_cases_blueprint.get("/admin/problems/<uuid:problem_id>/test-cases")
@admin_required
def list_admin_test_cases(problem_id: UUID):
    _get_problem_or_404(problem_id)

    statement = (
        select(TestCase)
        .where(TestCase.problem_id == problem_id)
        .order_by(TestCase.position.asc(), TestCase.created_at.asc())
    )
    test_cases = db.session.execute(statement).scalars().all()

    return jsonify({"test_cases": [serialize_test_case_summary(tc) for tc in test_cases]}), HTTPStatus.OK


@admin_test_cases_blueprint.post("/admin/problems/<uuid:problem_id>/test-cases")
@admin_required
def create_test_case(problem_id: UUID):
    problem = _get_problem_or_404(problem_id)
    payload = get_json_object()

    input_data = read_required_string(payload, "input_data")
    expected_output = read_required_string(payload, "expected_output")
    is_sample = read_optional_bool(payload, "is_sample")
    is_active = read_optional_bool(payload, "is_active")
    requested_position = read_optional_int(payload, "position", min_value=1)

    test_case_count = _get_test_case_count(problem.id)
    if requested_position is None:
        position = test_case_count + 1
    else:
        if requested_position > test_case_count + 1:
            raise BadRequest(
                f"Field 'position' must be less than or equal to {test_case_count + 1}."
            )
        position = requested_position

    try:
        if position <= test_case_count:
            _shift_positions_for_insert(problem_id=problem.id, from_position=position)

        test_case = TestCase.create(
            problem=problem,
            position=position,
            input_data=input_data,
            expected_output=expected_output,
            is_sample=False if is_sample is None else is_sample,
            is_active=True if is_active is None else is_active,
        )
        db.session.add(test_case)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Test case with the provided position already exists.") from error

    return jsonify({"test_case": serialize_test_case(test_case)}), HTTPStatus.CREATED


@admin_test_cases_blueprint.get("/admin/test-cases/<uuid:test_case_id>")
@admin_required
def get_admin_test_case(test_case_id: UUID):
    test_case = _get_test_case_or_404(test_case_id)
    return jsonify({"test_case": serialize_test_case(test_case)}), HTTPStatus.OK


@admin_test_cases_blueprint.patch("/admin/test-cases/<uuid:test_case_id>")
@admin_required
def update_admin_test_case(test_case_id: UUID):
    payload = get_json_object()
    test_case = _get_test_case_or_404(test_case_id)
    problem_id = test_case.problem_id

    try:
        if "input_data" in payload:
            test_case.set_input_data(read_required_string(payload, "input_data"))

        if "expected_output" in payload:
            test_case.set_expected_output(read_required_string(payload, "expected_output"))

        if "is_sample" in payload:
            is_sample = read_optional_bool(payload, "is_sample")
            if is_sample is None:
                raise BadRequest("Field 'is_sample' must not be null.")
            test_case.is_sample = is_sample

        if "is_active" in payload:
            is_active = read_optional_bool(payload, "is_active")
            if is_active is None:
                raise BadRequest("Field 'is_active' must not be null.")
            test_case.is_active = is_active

        if "position" in payload:
            new_position = read_required_int(payload, "position", min_value=1)
            max_position = _get_test_case_count(problem_id)
            if new_position > max_position:
                raise BadRequest(f"Field 'position' must be less than or equal to {max_position}.")
            _reorder_test_case(
                problem_id=problem_id,
                test_case=test_case,
                new_position=new_position,
            )

        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("Test case with the provided position already exists.") from error

    return jsonify({"test_case": serialize_test_case(test_case)}), HTTPStatus.OK