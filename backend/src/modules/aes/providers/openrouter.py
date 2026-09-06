"""OpenRouter provider — pydantic-ai Agent over OpenRouter's OpenAI-compatible API.

Use a `:free` model suffix for cost-free smoke tests.
"""

from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider as OpenRouterModelProvider

from ._pydantic_ai_support import run_agent
from .base import CorrectionCandidate, ProviderResponse


class OpenRouterProvider:
    def __init__(self, api_key: str, model: str) -> None:
        # pydantic-ai rejects an empty api_key at construction; registry builds providers eagerly even when unconfigured
        pydantic_model = OpenRouterModel(model, provider=OpenRouterModelProvider(api_key=api_key or "unset"))
        self.agent = Agent(pydantic_model, output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return await run_agent(
            self.agent,
            essay_text=essay_text,
            prompt=prompt,
            model_settings={"temperature": params.get("temperature", 0.0)},
        )
