"""Add essay_prompts with RLS.

Revision ID: a1b2c3d4e5f6
Revises: 412d82b1
Create Date: 2026-07-18 14:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "412d82b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "essay_prompts",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("enunciado", sa.Text(), nullable=False),
        sa.Column("ano_escolar", sa.String(length=2), nullable=False),
        sa.Column("genero_textual", sa.String(length=80), nullable=False),
        sa.Column("support_texts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rubric_id", sa.Integer(), nullable=False),
        sa.Column("prompt_template_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["rubric_id"],
            ["rubrics.id"],
        ),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"],
            ["prompt_templates.id"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_essay_prompts_municipio_id"), "essay_prompts", ["municipio_id"], unique=False)

    op.execute("ALTER TABLE essay_prompts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE essay_prompts FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON essay_prompts
        USING (
            municipio_id = NULLIF(current_setting('app.municipio_id', true), '')::int
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
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON essay_prompts")
    op.drop_index(op.f("ix_essay_prompts_municipio_id"), table_name="essay_prompts")
    op.drop_table("essay_prompts")
