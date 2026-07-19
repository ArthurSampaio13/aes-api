import uuid as uuid_pkg

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ....infrastructure.database.models import TimestampMixin, UUIDMixin
from ....infrastructure.database.session import Base


class Batch(Base, UUIDMixin, TimestampMixin):
    """A submission batch: one or more essays submitted together against one EssayPrompt."""

    __tablename__ = "batches"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    essay_prompt_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, ForeignKey("essay_prompts.uuid"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)


class Submission(Base, UUIDMixin, TimestampMixin):
    """One essay (text or image) within a Batch."""

    __tablename__ = "submissions"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    batch_id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, ForeignKey("batches.uuid"), nullable=False)
    input_type: Mapped[str] = mapped_column(String(10), nullable=False)
    original_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, default=None)
