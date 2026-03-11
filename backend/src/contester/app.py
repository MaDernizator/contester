from __future__ import annotations

import os

from flask import Flask

from contester.api import register_blueprints
from contester.auth import register_authentication
from contester.cli import register_commands
from contester.config import get_settings
from contester.error_handlers import register_error_handlers
from contester.extensions import db, migrate
from contester.logging_config import configure_logging


def create_app(environment: str | None = None) -> Flask:
    settings = get_settings(environment)

    configure_logging(settings.debug)

    app = Flask(__name__)
    app.config.from_mapping(settings.to_mapping())

    db.init_app(app)
    migrate.init_app(app, db)
    register_authentication(app)

    import contester.models  # noqa: F401

    register_blueprints(app)
    register_error_handlers(app)
    register_commands(app)

    app.logger.info("Application initialized in %s environment.", settings.environment)

    return app


def main() -> None:
    app = create_app()

    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "8000"))

    app.run(host=host, port=port, debug=app.config["DEBUG"])


if __name__ == "__main__":
    main()