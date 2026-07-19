"""Update key_permission_resource enum to AES resources.

Revision ID: 150f9d75c579
Revises: e4c48b355032
Create Date: 2026-07-19 16:12:15.537430
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "150f9d75c579"
down_revision: str | Sequence[str] | None = "e4c48b355032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_VALUES = (
    "CONVERSATIONS",
    "CREDITS",
    "AI_USAGE",
    "USER_PROFILE",
    "ANALYTICS",
    "ADMIN",
    "BILLING",
    "API_KEYS",
    "WILDCARD",
)
NEW_VALUES = ("BATCHES", "RUBRICS", "ESSAY_PROMPTS", "API_KEYS", "WILDCARD")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE keypermissionresource RENAME TO keypermissionresource_old")
    sa.Enum(*NEW_VALUES, name="keypermissionresource").create(op.get_bind())
    op.execute(
        "ALTER TABLE key_permissions ALTER COLUMN resource TYPE keypermissionresource "
        "USING resource::text::keypermissionresource"
    )
    op.execute("DROP TYPE keypermissionresource_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE keypermissionresource RENAME TO keypermissionresource_new")
    sa.Enum(*OLD_VALUES, name="keypermissionresource").create(op.get_bind())
    op.execute(
        "ALTER TABLE key_permissions ALTER COLUMN resource TYPE keypermissionresource "
        "USING resource::text::keypermissionresource"
    )
    op.execute("DROP TYPE keypermissionresource_new")
