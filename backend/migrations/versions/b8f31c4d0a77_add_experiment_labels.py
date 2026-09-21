"""Add source_label to submissions and run_label to correction jobs.

Revision ID: b8f31c4d0a77
Revises: d5e1a7c93f20
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8f31c4d0a77"
down_revision: str | None = "d5e1a7c93f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("source_label", sa.String(length=100), nullable=True))
    op.add_column("correction_jobs", sa.Column("run_label", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("correction_jobs", "run_label")
    op.drop_column("submissions", "source_label")
