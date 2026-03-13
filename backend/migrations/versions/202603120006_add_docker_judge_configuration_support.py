"""add docker judge configuration support

Revision ID: 202603120006
Revises: 202603120005
Create Date: 2026-03-12 00:06:00.000000

"""
from __future__ import annotations

# This revision is intentionally empty.
# Docker judge support in this stage is implemented via application configuration,
# infrastructure image, and runtime execution backend selection.
#
# A separate revision is still created to keep project history aligned with the
# feature rollout plan and to make deployment steps explicit.

from alembic import op

# revision identifiers, used by Alembic.
revision = "202603120006"
down_revision = "202603120005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass