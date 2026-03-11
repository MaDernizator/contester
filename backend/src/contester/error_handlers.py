from __future__ import annotations

from http import HTTPStatus

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        error_code = error.name.lower().replace(" ", "_")

        return (
            jsonify(
                {
                    "error": {
                        "code": error_code,
                        "message": error.description,
                    }
                }
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        app.logger.exception("Unhandled application error: %s", error)

        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "Internal server error.",
                    }
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
