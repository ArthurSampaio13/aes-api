"""Deterministic, free, no-network correction provider — the default everywhere except explicit real-provider
config."""

import json
from typing import Any

from .base import FIXED_CRITERIA, CorrectionCandidate, ProviderResponse


class MockProvider:
    model_id = "mock"

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        candidate_dict = {
            "scores": {c: {"nota": 3, "justificativa": f"Avaliação simulada para {c}."} for c in FIXED_CRITERIA},
            "feedback": "Feedback simulado: revise a coesão entre parágrafos.",
            "sugestao_acionavel": "Releia o segundo parágrafo e explicite a relação de causa e consequência.",
        }
        structured = CorrectionCandidate.model_validate(candidate_dict)

        return ProviderResponse(
            raw_text=str(candidate_dict),
            raw_request=json.dumps(
                {"model": "mock", "model_settings": params, "instructions": prompt, "user_content": essay_text},
                ensure_ascii=False,
                sort_keys=True,
            ),
            raw_response=json.dumps(candidate_dict, ensure_ascii=False, sort_keys=True),
            structured=structured,
            tokens_in=len(essay_text.split()) + len(prompt.split()),
            tokens_out=40,
            latency_ms=5,
        )
