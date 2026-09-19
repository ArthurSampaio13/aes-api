import json
from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from pydantic_ai import Agent, ModelRequest, ModelResponse, RequestUsage, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import AgentInfo, FunctionDef, FunctionModel
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openrouter import OpenRouterProvider

from src.infrastructure.config.settings import get_settings
from src.modules.aes.providers._pydantic_ai_support import (
    extract_raw_output_text,
    openrouter_model_settings,
    resolve_agent_model,
    run_agent,
    split_prompt_for_caching,
)
from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate

VALID_SCORES = {c: {"nota": 7, "justificativa": "ok"} for c in FIXED_CRITERIA}


def _agente_de_teste(responder: FunctionDef) -> Agent[object, CorrectionCandidate]:
    return Agent(FunctionModel(responder), output_type=CorrectionCandidate, retries={"output": 0})


def _resposta_do_modelo(usage: RequestUsage, provider_details: dict | None = None) -> ModelResponse:
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="final_result",
                args={"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "ok"},
            )
        ],
        usage=usage,
        provider_details=provider_details,
    )


@dataclass
class _DepsFalsos:
    events: list[dict[str, str]] = field(default_factory=list)


def test_extract_raw_output_text_reads_tool_call_args():
    messages = [
        ModelRequest(parts=[UserPromptPart(content="corrija isto")]),
        ModelResponse(parts=[ToolCallPart(tool_name="final_result", args={"feedback": "ok"})]),
    ]
    assert json.loads(extract_raw_output_text(messages)) == {"feedback": "ok"}


def test_extract_raw_output_text_reads_plain_text_when_no_tool_call():
    messages = [
        ModelRequest(parts=[UserPromptPart(content="corrija isto")]),
        ModelResponse(parts=[TextPart(content="resposta livre")]),
    ]
    assert extract_raw_output_text(messages) == "resposta livre"


def test_extract_raw_output_text_returns_empty_string_when_no_model_response():
    messages = [ModelRequest(parts=[UserPromptPart(content="corrija isto")])]
    assert extract_raw_output_text(messages) == ""


def test_split_prompt_for_caching_separates_prefix_from_essay():
    instructions, user_content = split_prompt_for_caching("Corrija: {essay_text}", "texto do aluno")
    assert instructions == "Corrija: "
    assert user_content == "texto do aluno"


def test_split_prompt_for_caching_handles_missing_placeholder():
    instructions, user_content = split_prompt_for_caching("sem placeholder", "texto do aluno")
    assert instructions == "sem placeholder"
    assert user_content == "texto do aluno"


def test_split_prompt_for_caching_handles_text_after_placeholder():
    instructions, user_content = split_prompt_for_caching("Antes {essay_text} depois", "texto")
    assert instructions == "Antes "
    assert user_content == "texto depois"


@pytest.fixture
def env_de_settings(monkeypatch):
    """get_settings() é lru_cache de processo; sem limpar na saída, um teste vaza settings para os seguintes."""
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_settings_carregam_seed_e_cache_de_instrucoes(env_de_settings):
    env_de_settings.setenv("AES_INFERENCE_SEED", "42")
    env_de_settings.setenv("AES_PROMPT_CACHE_TTL", "1h")
    get_settings.cache_clear()

    resultado = openrouter_model_settings(0.0)

    assert resultado["seed"] == 42
    assert resultado["openrouter_cache_instructions"] == "1h"
    assert resultado["temperature"] == 0.0


def test_sem_pin_configurado_o_provider_so_nega_coleta_de_dados(env_de_settings):
    env_de_settings.setenv("AES_OPENROUTER_PROVIDER_ORDER", "")
    get_settings.cache_clear()

    resultado = openrouter_model_settings(0.0)

    assert resultado["openrouter_provider"] == {"data_collection": "deny"}


def test_pin_configurado_desliga_fallback_para_a_rodada_ser_reproduzivel(env_de_settings):
    env_de_settings.setenv("AES_OPENROUTER_PROVIDER_ORDER", "anthropic, deepinfra")
    get_settings.cache_clear()

    resultado = openrouter_model_settings(0.0)

    assert resultado["openrouter_provider"] == {
        "data_collection": "deny",
        "order": ["anthropic", "deepinfra"],
        "allow_fallbacks": False,
    }


def test_pin_com_segmentos_vazios_ignora_virgulas_duplicadas(env_de_settings):
    env_de_settings.setenv("AES_OPENROUTER_PROVIDER_ORDER", "anthropic,,deepinfra,")
    get_settings.cache_clear()

    resultado = openrouter_model_settings(0.0)

    assert resultado["openrouter_provider"]["order"] == ["anthropic", "deepinfra"]


def test_prefixo_desconhecido_falha_alto_em_vez_de_cair_em_fallback():
    with pytest.raises(ValueError, match="Unsupported model prefix"):
        resolve_agent_model("anthropic:claude-sonnet-4.6")


@pytest.mark.asyncio
async def test_a_configuracao_de_cache_produz_cache_control_no_payload():
    """Regressao de e335cda: na 1.38 essa configuracao nao existia e nao fazia nada."""
    modelo = OpenRouterModel("anthropic/claude-sonnet-4.6", provider=OpenRouterProvider(api_key="x"))
    mensagens = [ModelRequest(parts=[UserPromptPart(content="redacao")], instructions="RUBRICA " * 20)]

    com_cache = await modelo._map_messages(
        mensagens, ModelRequestParameters(), model_settings=OpenRouterModelSettings(openrouter_cache_instructions="1h")
    )
    sem_cache = await modelo._map_messages(mensagens, ModelRequestParameters(), model_settings=OpenRouterModelSettings())

    assert "cache_control" in json.dumps(com_cache, default=str)
    assert "cache_control" not in json.dumps(sem_cache, default=str)


@pytest.mark.asyncio
async def test_served_provider_le_downstream_provider_que_o_adapter_openrouter_escreve():
    """`_map_openrouter_provider_details` no adapter OpenRouter só escreve `downstream_provider`.

    Sem checar essa chave primeiro, `served_provider` fica sempre `None` em produção mesmo com a
    chamada real servida por um backend identificável.
    """

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        return _resposta_do_modelo(
            RequestUsage(input_tokens=10, output_tokens=5),
            provider_details={"downstream_provider": "anthropic/claude-3.5-sonnet"},
        )

    resposta = await run_agent(
        _agente_de_teste(responder),
        essay_text="texto",
        prompt="RUBRICA {essay_text}",
        model_settings={},
        model_id="openrouter:modelo/teste",
    )

    assert resposta.served_provider == "anthropic/claude-3.5-sonnet"


@pytest.mark.asyncio
async def test_guardrail_events_chegam_ao_response_a_partir_de_deps():
    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        return _resposta_do_modelo(RequestUsage(input_tokens=10, output_tokens=5))

    eventos = [{"guard": "transcricao", "veredito": "retry", "motivo": "poucas palavras"}]
    deps = _DepsFalsos(events=eventos)

    resposta = await run_agent(
        _agente_de_teste(responder),
        essay_text="texto",
        prompt="RUBRICA {essay_text}",
        model_settings={},
        model_id="openrouter:modelo/teste",
        deps=deps,
    )

    assert resposta.guardrail_events == eventos


@pytest.mark.asyncio
async def test_cost_usd_reflete_o_custo_reportado_pelo_usage_da_rodada():
    """`cost_usd` reflete `usage.cost` sem alteração quando o `ModelResponse` já o traz pronto.

    `genai-prices` não precifica `FunctionModel`/`TestModel`, então o caso não-nulo só é
    exercitável aqui simulando o que o adapter OpenRouter faz de verdade: ler `usage.cost` do
    corpo da resposta e colocá-lo em `RequestUsage.cost`.
    """

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        return _resposta_do_modelo(RequestUsage(input_tokens=10, output_tokens=5, cost=Decimal("0.0042")))

    resposta = await run_agent(
        _agente_de_teste(responder),
        essay_text="texto",
        prompt="RUBRICA {essay_text}",
        model_settings={},
        model_id="openrouter:modelo/teste",
    )

    assert resposta.cost_usd == Decimal("0.0042")
