from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, session
from flask_login import login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, Unauthorized

from contester.auth import get_authenticated_user
from contester.extensions import db
from contester.models.user import User, UserRole
from contester.request_validation import (
    get_json_object,
    read_optional_string,
    read_required_string,
)
from contester.serializers import serialize_user

auth_blueprint = Blueprint("auth", __name__)


def _find_user_by_username(username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.session.scalar(statement)


def _find_user_by_email(email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.session.scalar(statement)


@auth_blueprint.post("/auth/register")
def register_participant():
    payload = get_json_object()

    username = read_required_string(payload, "username", max_length=32)
    password = read_required_string(payload, "password")
    email = read_optional_string(payload, "email", max_length=255)
    full_name = read_optional_string(payload, "full_name", max_length=128)

    normalized_email = email.lower() if email is not None else None

    if _find_user_by_username(username) is not None:
        raise Conflict("Username already exists.")

    if normalized_email is not None and _find_user_by_email(normalized_email) is not None:
        raise Conflict("Email already exists.")

    try:
        user = User.create(
            username=username,
            password=password,
            role=UserRole.PARTICIPANT,
            email=normalized_email,
            full_name=full_name,
        )
        db.session.add(user)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        raise BadRequest(str(error)) from error
    except IntegrityError as error:
        db.session.rollback()
        raise Conflict("User with the provided credentials already exists.") from error

    return jsonify({"user": serialize_user(user)}), HTTPStatus.CREATED


@auth_blueprint.post("/auth/login")
def login():
    payload = get_json_object()

    username = read_required_string(payload, "username", max_length=32)
    password = read_required_string(payload, "password")

    user = _find_user_by_username(username)
    if user is None or not user.is_active or not user.check_password(password):
        raise Unauthorized("Invalid username or password.")

    session.clear()
    session.permanent = True
    login_user(user)

    return jsonify({"user": serialize_user(user)}), HTTPStatus.OK


@auth_blueprint.post("/auth/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return "", HTTPStatus.NO_CONTENT


@auth_blueprint.get("/auth/me")
@login_required
def get_me():
    user = get_authenticated_user()
    return jsonify({"user": serialize_user(user)}), HTTPStatus.OK