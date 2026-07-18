"""Add batches and submissions with RLS.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-18 14:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6g7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "batches",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("essay_prompt_id", postgresql.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["essay_prompt_id"],
            ["essay_prompts.uuid"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_batches_municipio_id"), "batches", ["municipio_id"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", postgresql.UUID(), nullable=False),
        sa.Column("input_type", sa.String(length=10), nullable=False),
        sa.Column("original_ref", sa.String(length=500), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.uuid"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_submissions_municipio_id"), "submissions", ["municipio_id"], unique=False)

    for table in ("batches", "submissions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
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
    for table in ("batches", "submissions"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_index(op.f("ix_submissions_municipio_id"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_index(op.f("ix_batches_municipio_id"), table_name="batches")
    op.drop_table("batches")
