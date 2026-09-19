"""Shared helpers for pydantic-ai-backed CorrectionProviders."""

import json
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pydantic_ai import ModelMessage, ModelResponse, capture_run_messages
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider as OpenRouterModelProvider

from ....infrastructure.config.settings import get_settings
from .base import CorrectionCandidate, ProviderResponse

if TYPE_CHECKING:
    from pydantic_ai import Agent


def resolve_agent_model(model_id: str) -> Model:
    """O `Model` da pydantic-ai para `model_id`, construído a partir das settings, não do ambiente do processo.

    `infer_model` resolve a chave de API lendo `os.environ` diretamente; um `.env` carregado via
    `starlette.config.Config` nunca chega lá, então um worker corretamente configurado ainda falharia ao construir
    o provider. O OpenRouter — único provider que este sistema registra — contorna isso; qualquer outro prefixo
    segue pelo caminho genérico.
    """
    prefix, _, name = model_id.partition(":")
    if prefix == "openrouter":
        api_key = get_settings().OPENROUTER_API_KEY or "unset"
        return OpenRouterModel(name, provider=OpenRouterModelProvider(api_key=api_key))
    return infer_model(model_id)


def openrouter_model_settings(temperature: float) -> dict[str, Any]:
    """A folha digitalizada traz nome do aluno; nenhum provider que retenha dado deve recebê-la."""
    return {"temperature": temperature, "openrouter_provider": {"data_collection": "deny"}}


def extract_raw_output_text(messages: Sequence[ModelMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, ModelResponse):
            if message.tool_calls:
                return message.tool_calls[0].args_as_json_str()
            return message.text or ""
    return ""


def describe_request(model_id: str, instructions: str, user_content: str, model_settings: dict[str, Any]) -> str:
    """Everything that determined the answer, including the schema the model was given.

    The schema belongs here: a contract the model cannot satisfy looks identical to a
    model that simply refused, and only the recorded schema tells the two apart.
    """
    return json.dumps(
        {
            "model": model_id,
            "model_settings": model_settings,
            "instructions": instructions,
            "user_content": user_content,
            "output_schema": CorrectionCandidate.model_json_schema(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def dump_exchange(messages: Sequence[ModelMessage]) -> str:
    if not messages:
        return ""
    return ModelMessagesTypeAdapter.dump_json(list(messages)).decode()


def split_prompt_for_caching(prompt: str, essay_text: str) -> tuple[str, str]:
    prefix, _, suffix = prompt.partition("{essay_text}")
    return prefix, essay_text + suffix


async def run_agent(
    agent: "Agent[object, CorrectionCandidate]",
    essay_text: str,
    prompt: str,
    model_settings: dict[str, Any],
    model_id: str,
) -> ProviderResponse:
    """Run a pydantic-ai agent and map its result onto ProviderResponse.

    Shared by every pydantic-ai-backed provider so the usage accounting and the failure mapping stay identical across
    them.
    """
    instructions, user_content = split_prompt_for_caching(prompt, essay_text)
    raw_request = describe_request(model_id, instructions, user_content, model_settings)
    started_at = time.monotonic()

    with capture_run_messages() as exchange:
        try:
            result = await agent.run(user_content, instructions=instructions, model_settings=model_settings)  # type: ignore[call-overload]
        except Exception as exc:
            return ProviderResponse(
                raw_text="",
                raw_request=raw_request,
                raw_response=dump_exchange(exchange),
                structured=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                validation_error=str(exc),
                validation_error_type=type(exc).__name__,
            )

        usage = result.usage
        return ProviderResponse(
            raw_text=extract_raw_output_text(result.new_messages()),
            raw_request=raw_request,
            raw_response=dump_exchange(exchange),
            structured=result.output,
            tokens_in=usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens,
            tokens_out=usage.output_tokens,
            latency_ms=int((time.monotonic() - started_at) * 1000),
            validation_error=None,
        )
