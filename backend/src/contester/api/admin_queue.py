from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus

from flask import Blueprint, jsonify
from sqlalchemy import func, select

from contester.auth import admin_required
from contester.extensions import db
from contester.models.submission import Submission, SubmissionStatus

admin_queue_blueprint = Blueprint("admin_queue", __name__)


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


@admin_queue_blueprint.get("/admin/submissions/queue")
@admin_required
def get_submission_queue_status():
    pending_count = int(
        db.session.scalar(
            select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.PENDING)
        )
        or 0
    )
    running_count = int(
        db.session.scalar(
            select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.RUNNING)
        )
        or 0
    )
    finished_count = int(
        db.session.scalar(
            select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.FINISHED)
        )
        or 0
    )

    oldest_pending = db.session.execute(
        select(Submission.id, Submission.created_at)
        .where(Submission.status == SubmissionStatus.PENDING)
        .order_by(Submission.created_at.asc(), Submission.id.asc())
        .limit(1)
    ).first()

    return (
        jsonify(
            {
                "queue": {
                    "pending_count": pending_count,
                    "running_count": running_count,
                    "finished_count": finished_count,
                    "oldest_pending_submission_id": (
                        str(oldest_pending[0]) if oldest_pending is not None else None
                    ),
                    "oldest_pending_created_at": (
                        _serialize_optional_datetime(oldest_pending[1])
                        if oldest_pending is not None
                        else None
                    ),
                }
            }
        ),
        HTTPStatus.OK,
    )