from typing import Any

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....infrastructure.database.models import TimestampMixin
from ....infrastructure.database.session import Base


class Rubric(Base, TimestampMixin):
    """A versioned, immutable set of correction criteria.

    municipio_id NULL = platform default.
    """

    __tablename__ = "rubrics"

    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    municipio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("municipios.id"), index=True, default=None)


class PromptTemplate(Base, TimestampMixin):
    """A versioned, immutable LLM instruction template.

    municipio_id NULL = platform default.
    """

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    municipio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("municipios.id"), index=True, default=None)
