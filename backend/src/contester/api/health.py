from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, current_app, jsonify

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/health")
def healthcheck():
    return (
        jsonify(
            {
                "status": "ok",
                "service": current_app.config["APP_NAME"],
                "environment": current_app.config["APP_ENV"],
            }
        ),
        HTTPStatus.OK,
    )
