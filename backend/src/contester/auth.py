from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from flask import Flask, jsonify
from flask_login import current_user, login_required
from sqlalchemy import select
from werkzeug.exceptions import Forbidden

from contester.extensions import db, login_manager
from contester.models.user import User, UserRole

P = ParamSpec("P")
R = TypeVar("R")


def register_authentication(app: Flask) -> None:
    login_manager.init_app(app)
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            parsed_user_id = uuid.UUID(user_id)
        except ValueError:
            return None

        statement = select(User).where(
            User.id == parsed_user_id,
            User.is_active.is_(True),
        )
        return db.session.scalar(statement)

    @login_manager.unauthorized_handler
    def unauthorized():
        return (
            jsonify(
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "Authentication required.",
                    }
                }
            ),
            401,
        )


def roles_required(*allowed_roles: UserRole) -> Callable[[Callable[P, R]], Callable[P, R]]:
    allowed_role_set = set(allowed_roles)

    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        @wraps(view_func)
        @login_required
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            user = cast(User, current_user)
            if user.role not in allowed_role_set:
                raise Forbidden("You do not have permission to access this resource.")
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(view_func: Callable[P, R]) -> Callable[P, R]:
    return roles_required(UserRole.ADMIN)(view_func)


def get_authenticated_user() -> User:
    return cast(User, current_user)