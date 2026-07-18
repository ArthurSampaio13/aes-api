"""OpenRouter provider — OpenAI-compatible chat completions API.

Use a `:free` model suffix for cost-free smoke tests.
"""

import time
from typing import Any

import httpx
from pydantic import ValidationError

from .base import CorrectionCandidate, ProviderResponse

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        rendered_prompt = prompt.replace("{essay_text}", essay_text)
        started_at = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    _OPENROUTER_URL,
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": rendered_prompt}],
                        "temperature": params.get("temperature", 0.0),
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                usage = body.get("usage", {})
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            return ProviderResponse(
                raw_text="",
                structured=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                validation_error=str(exc),
            )
        latency_ms = int((time.monotonic() - started_at) * 1000)

        try:
            structured = CorrectionCandidate.model_validate_json(content)
            validation_error = None
        except ValidationError as exc:
            structured = None
            validation_error = str(exc)

        return ProviderResponse(
            raw_text=content,
            structured=structured,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            validation_error=validation_error,
        )
