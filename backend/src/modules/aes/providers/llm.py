"""Correção por qualquer modelo que a pydantic-ai saiba resolver."""

from typing import Any

from pydantic_ai import Agent

from ._pydantic_ai_support import resolve_agent_model, run_agent
from .base import CorrectionCandidate, ProviderResponse


class LLMCorrectionProvider:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.agent = Agent(resolve_agent_model(model_id), output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return await run_agent(
            self.agent,
            essay_text=essay_text,
            prompt=prompt,
            model_settings={"temperature": params.get("temperature", 0.0)},
            model_id=self.model_id,
        )
