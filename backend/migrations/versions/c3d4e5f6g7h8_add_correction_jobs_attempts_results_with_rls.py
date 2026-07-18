"""Add correction jobs, attempts, results with RLS.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-07-18 14:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6g7h8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6g7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "correction_jobs",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", postgresql.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.uuid"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_correction_jobs_municipio_id"), "correction_jobs", ["municipio_id"], unique=False)

    op.create_table(
        "correction_attempts",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("correction_job_id", postgresql.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("rubric_version", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("inference_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("raw_response_ref", sa.String(length=500), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["correction_job_id"],
            ["correction_jobs.uuid"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_correction_attempts_municipio_id"), "correction_attempts", ["municipio_id"], unique=False)

    op.create_table(
        "correction_results",
        sa.Column("uuid", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), nullable=False),
        sa.Column("correction_job_id", postgresql.UUID(), nullable=False),
        sa.Column("correction_attempt_id", postgresql.UUID(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("requires_teacher_review", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_id"],
            ["municipios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["correction_job_id"],
            ["correction_jobs.uuid"],
        ),
        sa.ForeignKeyConstraint(
            ["correction_attempt_id"],
            ["correction_attempts.uuid"],
        ),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("correction_job_id"),
    )
    op.create_index(op.f("ix_correction_results_municipio_id"), "correction_results", ["municipio_id"], unique=False)

    for table in ("correction_jobs", "correction_attempts", "correction_results"):
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
    for table in ("correction_jobs", "correction_attempts", "correction_results"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_index(op.f("ix_correction_results_municipio_id"), table_name="correction_results")
    op.drop_table("correction_results")
    op.drop_index(op.f("ix_correction_attempts_municipio_id"), table_name="correction_attempts")
    op.drop_table("correction_attempts")
    op.drop_index(op.f("ix_correction_jobs_municipio_id"), table_name="correction_jobs")
    op.drop_table("correction_jobs")
