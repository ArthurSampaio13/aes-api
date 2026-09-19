"""Add raw_request_ref to correction_attempts.

Revision ID: a7c2e9f41b58
Revises: f5a1c9d3b207
Create Date: 2026-09-19 11:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c2e9f41b58"
down_revision: str | Sequence[str] | None = "f5a1c9d3b207"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("correction_attempts", sa.Column("raw_request_ref", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("correction_attempts", "raw_request_ref")
