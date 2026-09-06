"""Shared helpers for pydantic-ai-backed CorrectionProviders."""

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pydantic_ai import ModelMessage, ModelResponse

from .base import CorrectionCandidate, ProviderResponse

if TYPE_CHECKING:
    from pydantic_ai import Agent


def extract_raw_output_text(messages: Sequence[ModelMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, ModelResponse):
            if message.tool_calls:
                return message.tool_calls[0].args_as_json_str()
            return message.text or ""
    return ""


def split_prompt_for_caching(prompt: str, essay_text: str) -> tuple[str, str]:
    prefix, _, suffix = prompt.partition("{essay_text}")
    return prefix, essay_text + suffix


async def run_agent(
    agent: "Agent[None, CorrectionCandidate]",
    essay_text: str,
    prompt: str,
    model_settings: dict[str, Any],
) -> ProviderResponse:
    """Run a pydantic-ai agent and map its result onto ProviderResponse.

    Shared by every pydantic-ai-backed provider so the usage accounting and the failure mapping stay identical across
    them.
    """
    instructions, user_content = split_prompt_for_caching(prompt, essay_text)
    started_at = time.monotonic()
    try:
        result = await agent.run(user_content, instructions=instructions, model_settings=model_settings)  # type: ignore[call-overload]
    except Exception as exc:
        return ProviderResponse(
            raw_text="",
            structured=None,
            tokens_in=0,
            tokens_out=0,
            latency_ms=int((time.monotonic() - started_at) * 1000),
            validation_error=str(exc),
            validation_error_type=type(exc).__name__,
        )

    usage = result.usage()
    return ProviderResponse(
        raw_text=extract_raw_output_text(result.new_messages()),
        structured=result.output,
        tokens_in=usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens,
        tokens_out=usage.output_tokens,
        latency_ms=int((time.monotonic() - started_at) * 1000),
        validation_error=None,
    )
