"""add cpp submission support

Revision ID: 202603120005
Revises: 202603120004
Create Date: 2026-03-12 00:05:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202603120005"
down_revision = "202603120004"
branch_labels = None
depends_on = None


OLD_LANGUAGE_ENUM = sa.Enum(
    "python",
    name="submission_language",
    native_enum=False,
)
NEW_LANGUAGE_ENUM = sa.Enum(
    "python",
    "cpp",
    name="submission_language",
    native_enum=False,
)

OLD_VERDICT_ENUM = sa.Enum(
    "pending",
    "accepted",
    "wrong_answer",
    "runtime_error",
    "time_limit_exceeded",
    "internal_error",
    "no_tests",
    name="submission_verdict",
    native_enum=False,
)
NEW_VERDICT_ENUM = sa.Enum(
    "pending",
    "accepted",
    "wrong_answer",
    "runtime_error",
    "time_limit_exceeded",
    "compilation_error",
    "internal_error",
    "no_tests",
    name="submission_verdict",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column(
            "language",
            existing_type=OLD_LANGUAGE_ENUM,
            type_=NEW_LANGUAGE_ENUM,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "verdict",
            existing_type=OLD_VERDICT_ENUM,
            type_=NEW_VERDICT_ENUM,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column(
            "verdict",
            existing_type=NEW_VERDICT_ENUM,
            type_=OLD_VERDICT_ENUM,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "language",
            existing_type=NEW_LANGUAGE_ENUM,
            type_=OLD_LANGUAGE_ENUM,
            existing_nullable=False,
        )