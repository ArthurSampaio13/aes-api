"""Shared helpers for pydantic-ai-backed CorrectionProviders."""

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic_ai import ModelMessage, ModelResponse, capture_run_messages
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models import Model
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
    o provider. O OpenRouter é o único provider que este sistema registra; qualquer outro prefixo é erro.
    """
    prefix, _, name = model_id.partition(":")
    if prefix != "openrouter":
        raise ValueError(f"Unsupported model prefix: {prefix}")
    api_key = get_settings().OPENROUTER_API_KEY or "unset"
    return OpenRouterModel(name, provider=OpenRouterModelProvider(api_key=api_key))


def openrouter_model_settings(temperature: float) -> dict[str, Any]:
    """A folha digitalizada traz nome do aluno; nenhum provider que retenha dado deve recebê-la.

    O pin de provedor existe para reprodutibilidade: sem ele o OpenRouter pode
    servir a mesma requisição de backends com quantizações diferentes.
    """
    settings = get_settings()
    provider: dict[str, Any] = {"data_collection": "deny"}
    ordem = [p.strip() for p in settings.AES_OPENROUTER_PROVIDER_ORDER.split(",") if p.strip()]
    if ordem:
        provider["order"] = ordem
        provider["allow_fallbacks"] = False
    return {
        "temperature": temperature,
        "seed": settings.AES_INFERENCE_SEED,
        "openrouter_cache_instructions": settings.AES_PROMPT_CACHE_TTL,
        "openrouter_provider": provider,
    }


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


def contar_respostas_do_modelo(messages: Sequence[ModelMessage]) -> int:
    return sum(isinstance(m, ModelResponse) for m in messages)


@dataclass
class UsoAcumulado:
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: Decimal | None = None


def somar_uso_do_modelo(messages: Sequence[ModelMessage]) -> UsoAcumulado:
    """Soma o `usage` de toda `ModelResponse` do exchange.

    Cada resposta do modelo já foi paga, mesmo quando a rodada termina em erro; um run que esgota o orçamento de retries
    de um guardrail fez `len(respostas)` chamadas reais e cobráveis.
    """
    uso = UsoAcumulado()
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        usage = message.usage
        uso.tokens_in += usage.input_tokens
        uso.tokens_out += usage.output_tokens
        uso.cache_read_tokens += usage.cache_read_tokens
        uso.cache_write_tokens += usage.cache_write_tokens
        if usage.cost is not None:
            uso.cost_usd = (uso.cost_usd or Decimal(0)) + usage.cost
    return uso


def provedor_servido(messages: Sequence[ModelMessage]) -> str | None:
    """O backend que de fato serviu a chamada.

    `downstream_provider` é a chave que o adapter OpenRouter da pydantic-ai realmente escreve em
    `provider_details` (`_map_openrouter_provider_details`). `provider_name` e `provider` ficam como
    fallback inofensivo para um adapter futuro de outro provider.
    """
    for message in reversed(messages):
        if isinstance(message, ModelResponse) and message.provider_details:
            provedor = (
                message.provider_details.get("downstream_provider")
                or message.provider_details.get("provider_name")
                or message.provider_details.get("provider")
            )
            if provedor:
                return str(provedor)
    return None


async def run_agent(
    agent: "Agent[object, CorrectionCandidate]",
    essay_text: str,
    prompt: str,
    model_settings: dict[str, Any],
    model_id: str,
    deps: Any = None,
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
            result = await agent.run(  # type: ignore[call-overload]
                user_content, instructions=instructions, model_settings=model_settings, deps=deps
            )
        except Exception as exc:
            uso = somar_uso_do_modelo(exchange)
            return ProviderResponse(
                raw_text="",
                raw_request=raw_request,
                raw_response=dump_exchange(exchange),
                structured=None,
                tokens_in=uso.tokens_in,
                tokens_out=uso.tokens_out,
                cache_read_tokens=uso.cache_read_tokens,
                cache_write_tokens=uso.cache_write_tokens,
                cost_usd=uso.cost_usd,
                served_provider=provedor_servido(exchange),
                latency_ms=int((time.monotonic() - started_at) * 1000),
                validation_error=str(exc),
                validation_error_type=type(exc).__name__,
                guardrail_events=list(getattr(deps, "events", deps) or []) if deps is not None else [],
                model_retries=max(contar_respostas_do_modelo(exchange) - 1, 0),
            )

        usage = result.usage
        eventos = list(getattr(deps, "events", deps) or []) if deps is not None else []
        return ProviderResponse(
            raw_text=extract_raw_output_text(result.new_messages()),
            raw_request=raw_request,
            raw_response=dump_exchange(exchange),
            structured=result.output,
            tokens_in=usage.input_tokens,
            tokens_out=usage.output_tokens,
            cache_read_tokens=usage.cache_read_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            cost_usd=usage.cost,
            served_provider=provedor_servido(exchange),
            guardrail_events=eventos,
            model_retries=max(contar_respostas_do_modelo(exchange) - 1, 0),
            latency_ms=int((time.monotonic() - started_at) * 1000),
            validation_error=None,
        )
