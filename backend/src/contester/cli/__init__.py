from __future__ import annotations

from flask import Flask

from contester.cli.judge import run_judge_worker_command
from contester.cli.users import create_admin_command


def register_commands(app: Flask) -> None:
    app.cli.add_command(create_admin_command)
    app.cli.add_command(run_judge_worker_command)