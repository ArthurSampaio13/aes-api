"""Add sugestao_acionavel to correction_results.

Revision ID: f5a1c9d3b207
Revises: 150f9d75c579
Create Date: 2026-09-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a1c9d3b207"
down_revision: str | Sequence[str] | None = "150f9d75c579"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "correction_results",
        sa.Column("sugestao_acionavel", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("correction_results", "sugestao_acionavel")
