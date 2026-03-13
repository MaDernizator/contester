from __future__ import annotations

from flask import Flask

from contester.api.admin import admin_blueprint
from contester.api.admin_contests import admin_contests_blueprint
from contester.api.admin_problems import admin_problems_blueprint
from contester.api.admin_queue import admin_queue_blueprint
from contester.api.admin_test_cases import admin_test_cases_blueprint
from contester.api.auth import auth_blueprint
from contester.api.contests import contests_blueprint
from contester.api.health import health_blueprint
from contester.api.problems import problems_blueprint
from contester.api.standings import standings_blueprint
from contester.api.submissions import submissions_blueprint


def register_blueprints(app: Flask) -> None:
    api_prefix = app.config["API_PREFIX"]

    app.register_blueprint(health_blueprint, url_prefix=api_prefix)
    app.register_blueprint(auth_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_contests_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_problems_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_queue_blueprint, url_prefix=api_prefix)
    app.register_blueprint(admin_test_cases_blueprint, url_prefix=api_prefix)
    app.register_blueprint(contests_blueprint, url_prefix=api_prefix)
    app.register_blueprint(problems_blueprint, url_prefix=api_prefix)
    app.register_blueprint(standings_blueprint, url_prefix=api_prefix)
    app.register_blueprint(submissions_blueprint, url_prefix=api_prefix)