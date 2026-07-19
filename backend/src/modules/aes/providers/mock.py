"""Deterministic, free, no-network correction provider — the default everywhere except explicit real-provider
config."""

from typing import Any

from pydantic import ValidationError

from .base import FIXED_CRITERIA, CorrectionCandidate, ProviderResponse


class MockProvider:
    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        candidate_dict = {
            "scores": {c: {"nota": 3, "justificativa": f"Avaliação simulada para {c}."} for c in FIXED_CRITERIA},
            "feedback": "Feedback simulado: revise a coesão entre parágrafos.",
            "sugestao_acionavel": "Releia o segundo parágrafo e explicite a relação de causa e consequência.",
        }
        try:
            structured = CorrectionCandidate.model_validate(candidate_dict)
            validation_error = None
        except ValidationError as exc:
            structured = None
            validation_error = str(exc)

        return ProviderResponse(
            raw_text=str(candidate_dict),
            structured=structured,
            tokens_in=len(essay_text.split()) + len(prompt.split()),
            tokens_out=40,
            latency_ms=5,
            validation_error=validation_error,
        )
