"""OpenRouter provider — pydantic-ai Agent over OpenRouter's OpenAI-compatible API.

Use a `:free` model suffix for cost-free smoke tests.
"""

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider as OpenRouterModelProvider

from ._pydantic_ai_support import extract_raw_output_text
from .base import CorrectionCandidate, ProviderResponse


class OpenRouterProvider:
    def __init__(self, api_key: str, model: str) -> None:
        pydantic_model = OpenRouterModel(model, provider=OpenRouterModelProvider(api_key=api_key or "unset"))
        self.agent = Agent(pydantic_model, output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        rendered_prompt = prompt.replace("{essay_text}", essay_text)
        started_at = time.monotonic()
        try:
            result = await self.agent.run(
                rendered_prompt,
                model_settings={"temperature": params.get("temperature", 0.0)},
            )
        except Exception as exc:
            return ProviderResponse(
                raw_text="",
                structured=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                validation_error=str(exc),
            )

        usage = result.usage()
        return ProviderResponse(
            raw_text=extract_raw_output_text(result.new_messages()),
            structured=result.output,
            tokens_in=usage.input_tokens,
            tokens_out=usage.output_tokens,
            latency_ms=int((time.monotonic() - started_at) * 1000),
            validation_error=None,
        )
