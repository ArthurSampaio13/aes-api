import json

import pytest
from pydantic_ai import ModelResponse, RequestUsage, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.llm import LLMCorrectionProvider

VALID_SCORES = {c: {"nota": 7, "justificativa": f"ok {c}"} for c in FIXED_CRITERIA}


def test_construction_succeeds_without_the_key_in_the_process_environment(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")
    assert provider.model_id == "openrouter:modelo/teste"


@pytest.mark.asyncio
async def test_parses_structured_output_and_usage():
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")
    test_model = TestModel(custom_output_args={"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "revise"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.validation_error is None
    assert response.structured is not None
    assert response.structured.feedback == "ok"
    assert response.tokens_in > 0


@pytest.mark.asyncio
async def test_reports_the_model_it_was_built_with():
    assert LLMCorrectionProvider(model_id="openrouter:modelo/teste").model_id == "openrouter:modelo/teste"


@pytest.mark.asyncio
async def test_records_both_sides_even_when_output_is_invalid():
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")
    test_model = TestModel(custom_output_args={"scores": {}, "feedback": "ok", "sugestao_acionavel": "ok"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None
    assert response.raw_request and response.raw_response

    request = json.loads(response.raw_request)
    assert request["model"] == "openrouter:modelo/teste"
    assert request["model_settings"]["temperature"] == 0.0
    assert "corrija:" in request["instructions"]
    assert request["user_content"] == "texto"
    assert sorted(request["output_schema"]["$defs"]["CriterionScores"]["required"]) == sorted(FIXED_CRITERIA)


@pytest.mark.asyncio
async def test_cache_tokens_ficam_fora_de_tokens_in_para_o_budget_nao_cobrar_cache():
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "revise"},
                )
            ],
            usage=RequestUsage(input_tokens=100, output_tokens=20, cache_read_tokens=900, cache_write_tokens=50),
        )

    with provider.agent.override(model=FunctionModel(responder)):
        resposta = await provider.correct(essay_text="texto", prompt="RUBRICA {essay_text}", params={})

    assert resposta.tokens_in == 100
    assert resposta.cache_read_tokens == 900
    assert resposta.cache_write_tokens == 50
    assert resposta.model_retries == 0


@pytest.mark.asyncio
async def test_citacao_inventada_provoca_nova_chamada_ao_modelo():
    chamadas: list = []
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        chamadas.append(messages)
        primeira = len(chamadas) == 1
        justificativa = 'O aluno escreve "voou sobre a montanha" sem coesao.' if primeira else "Coesao adequada."
        scores = {c: {"nota": 7, "justificativa": f"{justificativa} {c}"} for c in FIXED_CRITERIA}
        output = {"scores": scores, "feedback": "ok", "sugestao_acionavel": "revise"}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    with provider.agent.override(model=FunctionModel(responder)):
        resposta = await provider.correct(
            essay_text="O menino caminhou ate a escola.", prompt="RUBRICA {essay_text}", params={}
        )

    assert len(chamadas) == 2
    assert resposta.structured is not None
    assert resposta.model_retries == 1
    assert [e["veredito"] for e in resposta.guardrail_events][0] == "retry"


@pytest.mark.asyncio
async def test_citacao_ancorada_na_redacao_passa_de_primeira():
    chamadas: list = []
    provider = LLMCorrectionProvider(model_id="openrouter:modelo/teste")

    def responder(messages: list, info: AgentInfo) -> ModelResponse:
        chamadas.append(messages)
        scores = {c: {"nota": 7, "justificativa": f'Usa "caminhou ate a escola" bem em {c}.'} for c in FIXED_CRITERIA}
        output = {"scores": scores, "feedback": "ok", "sugestao_acionavel": "revise"}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    with provider.agent.override(model=FunctionModel(responder)):
        resposta = await provider.correct(
            essay_text="O menino caminhou ate a escola.", prompt="RUBRICA {essay_text}", params={}
        )

    assert len(chamadas) == 1
    assert resposta.structured is not None
