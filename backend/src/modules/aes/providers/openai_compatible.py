"""Correction provider for any OpenAI-compatible LLM gateway.

One class covers every gateway that speaks the OpenAI chat API; a gateway is a
`base_url` plus a key, not a new implementation. Presets below were verified to
offer a no-credit-card free tier on 2026-09-05 — free tiers change often, so
re-check before relying on one.

Cerebras note: structured output support is model-dependent there. Models that
reject `tools` and `response_format` together will surface as validation errors
rather than corrections.
"""

from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ._pydantic_ai_support import run_agent
from .base import CorrectionCandidate, ProviderResponse

GATEWAY_BASE_URLS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "github": "https://models.github.ai/inference",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url
        # pydantic-ai rejects an empty api_key at construction; the registry builds providers eagerly even when unconfigured
        pydantic_model = OpenAIChatModel(model, provider=OpenAIProvider(base_url=base_url, api_key=api_key or "unset"))
        self.agent: Agent[None, CorrectionCandidate] = Agent(pydantic_model, output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        return await run_agent(
            self.agent,
            essay_text=essay_text,
            prompt=prompt,
            model_settings={"temperature": params.get("temperature", 0.0)},
        )
