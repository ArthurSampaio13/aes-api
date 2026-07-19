"""Add code_version to correction_attempts.

Revision ID: e4c48b355032
Revises: c3d4e5f6g7h8
Create Date: 2026-07-19 02:14:25.444073
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4c48b355032"
down_revision: str | Sequence[str] | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("correction_attempts", sa.Column("code_version", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("correction_attempts", "code_version")
