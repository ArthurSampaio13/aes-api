"""Amazon Bedrock provider — Converse API via aioboto3."""

import time
from collections.abc import Callable
from typing import Any

import aioboto3
from pydantic import ValidationError

from .base import CorrectionCandidate, ProviderResponse


class BedrockProvider:
    def __init__(self, model_id: str, client_factory: Callable[[], Any] | None = None) -> None:
        self._model_id = model_id
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> Any:
        session = aioboto3.Session()
        return session.client("bedrock-runtime")

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        rendered_prompt = prompt.replace("{essay_text}", essay_text)
        started_at = time.monotonic()
        try:
            async with self._client_factory() as client:
                response = await client.converse(
                    modelId=self._model_id,
                    messages=[{"role": "user", "content": [{"text": rendered_prompt}]}],
                    inferenceConfig={"temperature": params.get("temperature", 0.0)},
                )
                content = response["output"]["message"]["content"][0]["text"]
                usage = response.get("usage") or {}
                tokens_in = usage.get("inputTokens", 0)
                tokens_out = usage.get("outputTokens", 0)
        except Exception as exc:
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
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            validation_error=validation_error,
        )
