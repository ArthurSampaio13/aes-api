"""Add cost_source to correction attempts.

Revision ID: d5e1a7c93f20
Revises: cf7a2a2e8d11
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e1a7c93f20"
down_revision: str | None = "cf7a2a2e8d11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("correction_attempts", sa.Column("cost_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("correction_attempts", "cost_source")
