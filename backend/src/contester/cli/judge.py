from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext

from contester.services import SubmissionQueueService


@click.command("run-judge-worker")
@click.option("--once", is_flag=True, help="Process all currently pending submissions and exit.")
@with_appcontext
def run_judge_worker_command(once: bool) -> None:
    service = SubmissionQueueService.from_app_config()
    running_timeout_sec = int(current_app.config["JUDGE_RUNNING_SUBMISSION_TIMEOUT_SEC"])

    if once:
        processed_count = service.run_once(running_timeout_sec=running_timeout_sec)
        click.echo(f"Processed {processed_count} submission(s).")
        return

    click.echo("Judge worker started.")
    service.run_forever(
        poll_interval_sec=int(current_app.config["JUDGE_POLL_INTERVAL_SEC"]),
        running_timeout_sec=running_timeout_sec,
    )