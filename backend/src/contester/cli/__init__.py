from __future__ import annotations

from flask import Flask

from contester.cli.users import create_admin_command


def register_commands(app: Flask) -> None:
    app.cli.add_command(create_admin_command)