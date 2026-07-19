"""Shared helpers for pydantic-ai-backed CorrectionProviders."""

from collections.abc import Sequence

from pydantic_ai import ModelMessage, ModelResponse


def extract_raw_output_text(messages: Sequence[ModelMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, ModelResponse):
            if message.tool_calls:
                return message.tool_calls[0].args_as_json_str()
            return message.text or ""
    return ""
