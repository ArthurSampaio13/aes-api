from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....infrastructure.database.models import TimestampMixin, UUIDMixin
from ....infrastructure.database.session import Base


class EssayPrompt(Base, UUIDMixin, TimestampMixin):
    """A writing prompt a teacher creates: statement, grade, genre, support texts, active rubric+prompt version."""

    __tablename__ = "essay_prompts"

    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("municipios.id"), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    ano_escolar: Mapped[str] = mapped_column(String(2), nullable=False)
    genero_textual: Mapped[str] = mapped_column(String(80), nullable=False)
    rubric_id: Mapped[int] = mapped_column(Integer, ForeignKey("rubrics.id"), nullable=False)
    prompt_template_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompt_templates.id"), nullable=False)
    support_texts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default_factory=list)
