from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupportText(BaseModel):
    titulo: str
    conteudo: str


class EssayPromptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: Annotated[str, Field(min_length=1, max_length=200)]
    enunciado: Annotated[str, Field(min_length=1)]
    ano_escolar: Annotated[str, Field(pattern=r"^[6-9]$")]
    genero_textual: Annotated[str, Field(min_length=1, max_length=80)]
    support_texts: list[SupportText] = Field(default_factory=list)
    rubric_id: int
    prompt_template_id: int


class EssayPromptCreateInternal(EssayPromptCreate):
    municipio_id: int


class EssayPromptRead(BaseModel):
    uuid: UUID
    municipio_id: int
    titulo: str
    enunciado: str
    ano_escolar: str
    genero_textual: str
    support_texts: list[SupportText]
    rubric_id: int
    prompt_template_id: int
