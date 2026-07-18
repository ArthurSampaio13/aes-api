"""Add municipios table and user.municipio_id.

Revision ID: 001_add_municipios
Revises: None
Create Date: 2026-07-18 13:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_add_municipios"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "municipios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("monthly_token_budget", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_municipios")),
        sa.UniqueConstraint("nome", name=op.f("uq_municipios_nome")),
    )
    op.add_column("user", sa.Column("municipio_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_user_municipio_id"), "user", ["municipio_id"], unique=False)
    op.create_foreign_key(op.f("fk_user_municipio_id_municipios"), "user", "municipios", ["municipio_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_user_municipio_id_municipios"), "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_municipio_id"), table_name="user")
    op.drop_column("user", "municipio_id")
    op.drop_table("municipios")
