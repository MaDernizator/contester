"""create test cases and submissions tables

Revision ID: 202603120004
Revises: 202603120003
Create Date: 2026-03-12 00:04:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202603120004"
down_revision = "202603120003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "test_cases",
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_sample", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 1", name=op.f("ck_test_cases_test_case_position_positive")),
        sa.ForeignKeyConstraint(
            ["problem_id"],
            ["problems.id"],
            name=op.f("fk_test_cases_problem_id_problems"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_cases")),
        sa.UniqueConstraint("problem_id", "position", name="uq_test_cases_problem_position"),
    )
    op.create_index(op.f("ix_test_cases_problem_id"), "test_cases", ["problem_id"], unique=False)
    op.create_index(op.f("ix_test_cases_is_active"), "test_cases", ["is_active"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column(
            "language",
            sa.Enum("python", name="submission_language", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "finished", name="submission_status", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "verdict",
            sa.Enum(
                "pending",
                "accepted",
                "wrong_answer",
                "runtime_error",
                "time_limit_exceeded",
                "internal_error",
                "no_tests",
                name="submission_verdict",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("passed_test_count", sa.Integer(), nullable=False),
        sa.Column("total_test_count", sa.Integer(), nullable=False),
        sa.Column("failed_test_position", sa.Integer(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("judge_log", sa.Text(), nullable=True),
        sa.Column("judged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["problem_id"],
            ["problems.id"],
            name=op.f("fk_submissions_problem_id_problems"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_submissions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submissions")),
    )
    op.create_index(op.f("ix_submissions_user_id"), "submissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_submissions_problem_id"), "submissions", ["problem_id"], unique=False)
    op.create_index(op.f("ix_submissions_language"), "submissions", ["language"], unique=False)
    op.create_index(op.f("ix_submissions_status"), "submissions", ["status"], unique=False)
    op.create_index(op.f("ix_submissions_verdict"), "submissions", ["verdict"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_submissions_verdict"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_status"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_language"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_problem_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_user_id"), table_name="submissions")
    op.drop_table("submissions")

    op.drop_index(op.f("ix_test_cases_is_active"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_problem_id"), table_name="test_cases")
    op.drop_table("test_cases")