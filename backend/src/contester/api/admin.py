from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify

from contester.auth import admin_required, get_authenticated_user
from contester.serializers import serialize_user

admin_blueprint = Blueprint("admin", __name__)


@admin_blueprint.get("/admin/session")
@admin_required
def get_admin_session():
    user = get_authenticated_user()
    return (
        jsonify(
            {
                "status": "ok",
                "user": serialize_user(user),
            }
        ),
        HTTPStatus.OK,
    )