from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base


class Municipio(Base, TimestampMixin):
    """A tenant of the platform (a Brazilian municipality)."""

    __tablename__ = "municipios"

    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    monthly_token_budget: Mapped[int | None] = mapped_column(Integer, default=None)

    def __repr__(self) -> str:
        return self.nome
