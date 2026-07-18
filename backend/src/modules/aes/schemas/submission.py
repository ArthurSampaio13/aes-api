from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BatchSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    essay_prompt_uuid: UUID
    texts: Annotated[list[str], Field(min_length=1, max_length=500)]
    provider: str = "mock"
    model: str = "mock-v1"


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
    requires_teacher_review: bool
