"""Correção por qualquer modelo que a pydantic-ai saiba resolver."""

from typing import Any

from pydantic_ai import Agent
from pydantic_ai_harness import OutputGuardrail

from ....infrastructure.config.settings import get_settings
from ._pydantic_ai_support import openrouter_model_settings, resolve_agent_model, run_agent
from .base import CorrectionCandidate, ProviderResponse
from .guardrails import CorrectionDeps, guard_citacoes, guard_justificativas_distintas


class LLMCorrectionProvider:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        guardrail = OutputGuardrail[CorrectionDeps](
            guard=[guard_citacoes, guard_justificativas_distintas]  # type: ignore[list-item]
        )
        self.agent = Agent(
            resolve_agent_model(model_id),
            output_type=CorrectionCandidate,
            deps_type=CorrectionDeps,
            retries={"output": get_settings().AES_CORRECTION_MAX_RETRIES},
            capabilities=[guardrail],
        )

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return await run_agent(
            self.agent,  # type: ignore[arg-type]
            essay_text=essay_text,
            prompt=prompt,
            model_settings=openrouter_model_settings(params.get("temperature", 0.0)),
            model_id=self.model_id,
            deps=CorrectionDeps(essay_text=essay_text),
        )
