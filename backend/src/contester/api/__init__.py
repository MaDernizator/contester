from __future__ import annotations

from flask import Flask

from contester.api.health import health_blueprint


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_blueprint, url_prefix=app.config["API_PREFIX"])
