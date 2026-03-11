"""create contests table

Revision ID: 202603120002
Revises: 202603120001
Create Date: 2026-03-12 00:02:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202603120002"
down_revision = "202603120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contests",
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="contest_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name=op.f("ck_contests_contest_schedule_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_contests_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contests")),
        sa.UniqueConstraint("slug", name=op.f("uq_contests_slug")),
    )
    op.create_index(op.f("ix_contests_created_by_id"), "contests", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_contests_status"), "contests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contests_status"), table_name="contests")
    op.drop_index(op.f("ix_contests_created_by_id"), table_name="contests")
    op.drop_table("contests")