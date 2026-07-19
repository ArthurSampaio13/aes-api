"""Amazon Bedrock provider — pydantic-ai Agent over the Bedrock Converse API."""

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel

from ._pydantic_ai_support import extract_raw_output_text, split_prompt_for_caching
from .base import CorrectionCandidate, ProviderResponse


class BedrockProvider:
    def __init__(self, model_id: str) -> None:
        pydantic_model = BedrockConverseModel(model_id)
        self.agent = Agent(pydantic_model, output_type=CorrectionCandidate, output_retries=0)

    async def correct(self, essay_text: str, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        instructions, user_content = split_prompt_for_caching(prompt, essay_text)
        started_at = time.monotonic()
        try:
            result = await self.agent.run(  # type: ignore[call-overload]
                user_content,
                instructions=instructions,
                model_settings={
                    "temperature": params.get("temperature", 0.0),
                    "bedrock_cache_instructions": True,
                },
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
