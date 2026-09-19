"""Provider-agnostic contract for LLM essay correction.

All five rubric criteria are fixed by AGENTS.md.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

FIXED_CRITERIA = ["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]

CriterionName = Literal["adequacao_tema", "estrutura_textual", "coesao_coerencia", "adequacao_ling", "vocabulario"]


class CriterionScore(BaseModel):
    nota: int = Field(ge=0, le=10)
    justificativa: str = Field(min_length=1)


class CriterionScores(BaseModel):
    """Explicit fields, not a dict keyed by CriterionName.

    A dict renders as `propertyNames.enum` in the JSON Schema, which names the
    allowed keys without requiring any, so a model may answer `{}` and still be
    schema-valid. Declaring the five as fields puts them in `required`, which is
    the only part of the contract a model actually sees.
    """

    model_config = ConfigDict(extra="forbid")

    adequacao_tema: CriterionScore
    estrutura_textual: CriterionScore
    coesao_coerencia: CriterionScore
    adequacao_ling: CriterionScore
    vocabulario: CriterionScore


class CorrectionCandidate(BaseModel):
    scores: CriterionScores
    feedback: str = Field(min_length=1)
    sugestao_acionavel: str = Field(min_length=1)


class ProviderResponse(BaseModel):
    raw_text: str
    raw_request: str = ""
    raw_response: str = ""
    structured: CorrectionCandidate | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    validation_error: str | None = None
    validation_error_type: str | None = None


class CorrectionProvider(Protocol):
    model_id: str

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        ...
