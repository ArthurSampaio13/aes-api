"""Add rubrics and prompt_templates with RLS.

Revision ID: 412d82b1
Revises: 3da3ed5e37b1
Create Date: 2026-07-18 14:03:21.107868
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "412d82b1"
down_revision: str | Sequence[str] | None = "3da3ed5e37b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rubrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(op.f("ix_rubrics_municipio_id"), "rubrics", ["municipio_id"], unique=False)
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(op.f("ix_prompt_templates_municipio_id"), "prompt_templates", ["municipio_id"], unique=False)

    for table in ("rubrics", "prompt_templates"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                municipio_id = NULLIF(current_setting('app.municipio_id', true), '')::int
                OR municipio_id IS NULL
                OR current_setting('app.is_superuser', true)::boolean
            )
            WITH CHECK (
                municipio_id = NULLIF(current_setting('app.municipio_id', true), '')::int
                OR current_setting('app.is_superuser', true)::boolean
            )
        """
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("rubrics", "prompt_templates"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_index(op.f("ix_prompt_templates_municipio_id"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_index(op.f("ix_rubrics_municipio_id"), table_name="rubrics")
    op.drop_table("rubrics")
