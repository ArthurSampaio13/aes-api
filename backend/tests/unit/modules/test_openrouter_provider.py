import pytest
from pydantic_ai import ModelResponse, RequestUsage, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_openrouter_provider_parses_usage_and_content():
    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    scores = {
        "adequacao_tema": {"nota": 7, "justificativa": "ok"},
        "estrutura_textual": {"nota": 7, "justificativa": "ok"},
        "coesao_coerencia": {"nota": 7, "justificativa": "ok"},
        "adequacao_ling": {"nota": 7, "justificativa": "ok"},
        "vocabulario": {"nota": 7, "justificativa": "ok"},
    }
    test_model = TestModel(
        custom_output_args={"scores": scores, "feedback": "ok", "sugestao_acionavel": "revise o segundo parágrafo"}
    )

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.validation_error is None
    assert response.structured is not None
    assert response.structured.feedback == "ok"
    assert response.tokens_in > 0
    assert response.tokens_out > 0


@pytest.mark.asyncio
async def test_openrouter_provider_returns_validation_error_on_incomplete_output():
    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    test_model = TestModel(custom_output_args={"scores": {}, "feedback": "ok", "sugestao_acionavel": "ok"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_openrouter_provider_returns_validation_error_on_model_failure():
    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")

    def raise_rate_limit(messages: list, info: AgentInfo):
        raise RuntimeError("rate limited")

    with provider.agent.override(model=FunctionModel(raise_rate_limit)):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_openrouter_provider_splits_static_prefix_into_cacheable_instructions():
    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    captured = {}

    def capture_call(messages: list, info: AgentInfo):
        captured["instructions"] = info.instructions
        captured["user_content"] = messages[-1].parts[-1].content
        raise RuntimeError("stop after capture")

    with provider.agent.override(model=FunctionModel(capture_call)):
        prompt_with_json_example = 'Responda como {"scores": {}, "feedback": "..."}. Redação: {essay_text}'
        await provider.correct(essay_text="texto do aluno", prompt=prompt_with_json_example, params={})

    # pydantic-ai's Agent.run strips the joined instructions string (agent/__init__.py get_instructions:
    # `'\n\n'.join(parts).strip()`), so trailing whitespace from the static prefix does not survive.
    assert captured["instructions"] == 'Responda como {"scores": {}, "feedback": "..."}. Redação:'
    assert captured["user_content"] == "texto do aluno"


@pytest.mark.asyncio
async def test_openrouter_provider_folds_cache_tokens_into_tokens_in():
    provider = OpenRouterProvider(api_key="test-key", model="meta-llama/llama-3-8b-instruct:free")
    scores = {
        "adequacao_tema": {"nota": 6, "justificativa": "ok"},
        "estrutura_textual": {"nota": 6, "justificativa": "ok"},
        "coesao_coerencia": {"nota": 6, "justificativa": "ok"},
        "adequacao_ling": {"nota": 6, "justificativa": "ok"},
        "vocabulario": {"nota": 6, "justificativa": "ok"},
    }

    def return_cached_response(messages: list, info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args={"scores": scores, "feedback": "ok", "sugestao_acionavel": "ok"},
                )
            ],
            usage=RequestUsage(input_tokens=10, output_tokens=50, cache_read_tokens=200, cache_write_tokens=0),
        )

    with provider.agent.override(model=FunctionModel(return_cached_response)):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.tokens_in == 210
    assert response.tokens_out == 50
