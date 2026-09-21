"""Saída de auditoria de um batch: as condições completas de cada correção.

O mesmo formato serve de cabeçalho do relatório de avaliação, para que export da API e experimento não divirjam.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AttemptManifest(BaseModel):
    attempt_number: int
    outcome: str
    provider: str
    model: str
    served_provider: str | None
    prompt_version: int
    rubric_version: int
    code_version: str | None
    inference_params: dict[str, Any]
    tokens_in: int | None
    tokens_out: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    cost_usd: Decimal | None
    cost_source: str | None
    latency_ms: int | None
    model_retries: int | None
    guardrail_events: list[dict[str, Any]] | None
    raw_request_ref: str | None
    raw_response_ref: str | None
    error_message: str | None
    created_at: datetime


class ResultManifest(BaseModel):
    scores: dict[str, Any]
    feedback: str
    sugestao_acionavel: str
    requires_teacher_review: bool


class JobManifest(BaseModel):
    job_id: UUID
    submission_id: UUID
    source_label: str | None
    run_label: str | None
    status: str
    input_type: str
    transcription: dict[str, Any] | None
    attempts: list[AttemptManifest]
    result: ResultManifest | None


class BatchManifest(BaseModel):
    batch_id: UUID
    essay_prompt_id: UUID
    created_at: datetime
    jobs: list[JobManifest]
