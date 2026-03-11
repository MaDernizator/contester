from __future__ import annotations

from flask import Flask

from contester.api.admin import admin_blueprint
from contester.api.auth import auth_blueprint
from contester.api.health import health_blueprint


def register_blueprints(app: Flask) -> None:
    api_prefix = app.config["API_PREFIX"]

    app.register_blueprint(health_blueprint, url_prefix=api_prefix)
    app.register_blueprint(auth_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_blueprint, url_prefix=api_prefix)