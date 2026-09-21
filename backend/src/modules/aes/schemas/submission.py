from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BatchSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    essay_prompt_uuid: UUID
    texts: Annotated[list[str], Field(min_length=1, max_length=500)]
    labels: Annotated[list[str] | None, Field(default=None, max_length=500)]
    run_label: Annotated[str | None, Field(default=None, max_length=50)]
    provider: str = "mock"
    model: str | None = None


class BatchRecorrectRequest(BaseModel):
    """Nova execução sobre as redações que o lote já tem."""

    model_config = ConfigDict(extra="forbid")

    run_label: Annotated[str | None, Field(default=None, max_length=50)]
    provider: str = "mock"
    model: str | None = None


class BatchSubmitResponse(BaseModel):
    batch_id: UUID
    job_ids: list[UUID]


class JobStatusRead(BaseModel):
    job_id: UUID
    status: str
    provider: str
    model: str


class JobResultRead(BaseModel):
    scores: dict
    feedback: str
    sugestao_acionavel: str
    requires_teacher_review: bool
