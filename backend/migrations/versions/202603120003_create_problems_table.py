"""create problems table

Revision ID: 202603120003
Revises: 202603120002
Create Date: 2026-03-12 00:03:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202603120003"
down_revision = "202603120002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("contest_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("input_specification", sa.Text(), nullable=True),
        sa.Column("output_specification", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sample_input", sa.Text(), nullable=True),
        sa.Column("sample_output", sa.Text(), nullable=True),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="problem_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("memory_limit_mb >= 16", name=op.f("ck_problems_problem_memory_limit_valid")),
        sa.CheckConstraint("position >= 1", name=op.f("ck_problems_problem_position_positive")),
        sa.CheckConstraint("time_limit_ms >= 100", name=op.f("ck_problems_problem_time_limit_valid")),
        sa.ForeignKeyConstraint(
            ["contest_id"],
            ["contests.id"],
            name=op.f("fk_problems_contest_id_contests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problems")),
        sa.UniqueConstraint("contest_id", "code", name="uq_problems_contest_code"),
    )
    op.create_index(op.f("ix_problems_contest_id"), "problems", ["contest_id"], unique=False)
    op.create_index(op.f("ix_problems_status"), "problems", ["status"], unique=False)
    op.create_index("ix_problems_contest_position", "problems", ["contest_id", "position"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_problems_contest_position", table_name="problems")
    op.drop_index(op.f("ix_problems_status"), table_name="problems")
    op.drop_index(op.f("ix_problems_contest_id"), table_name="problems")
    op.drop_table("problems")