"""Provider-agnostic contract for LLM essay correction.

All five rubric criteria are fixed by AGENTS.md.
"""

from typing import Any, Protocol

from pydantic import BaseModel, Field

FIXED_CRITERIA = ["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]


class CriterionScore(BaseModel):
    nota: int = Field(ge=0, le=10)
    justificativa: str = Field(min_length=1)


class CorrectionCandidate(BaseModel):
    scores: dict[str, CriterionScore]
    feedback: str = Field(min_length=1)


class ProviderResponse(BaseModel):
    raw_text: str
    structured: CorrectionCandidate | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    validation_error: str | None = None


class CorrectionProvider(Protocol):
    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        ...
