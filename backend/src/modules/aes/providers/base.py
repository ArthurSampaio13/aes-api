"""Provider-agnostic contract for LLM essay correction.

All five rubric criteria are fixed by AGENTS.md.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

FIXED_CRITERIA = ["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]

CriterionName = Literal["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]


class CriterionScore(BaseModel):
    nota: int = Field(ge=0, le=10)
    justificativa: str = Field(min_length=1)


class CorrectionCandidate(BaseModel):
    scores: dict[CriterionName, CriterionScore]
    feedback: str = Field(min_length=1)
    sugestao_acionavel: str = Field(min_length=1)

    @model_validator(mode="after")
    def _require_all_criteria(self) -> "CorrectionCandidate":
        missing = set(FIXED_CRITERIA) - set(self.scores)
        if missing:
            raise ValueError(f"missing scores for criteria: {sorted(missing)}")
        return self


class ProviderResponse(BaseModel):
    raw_text: str
    structured: CorrectionCandidate | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    validation_error: str | None = None
    validation_error_type: str | None = None


class CorrectionProvider(Protocol):
    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        ...
