import pytest
from pydantic_ai import ModelResponse, RequestUsage, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.bedrock import BedrockProvider


@pytest.mark.asyncio
async def test_bedrock_provider_parses_usage_and_content():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    scores = {
        "adequacao_tema": {"nota": 6, "justificativa": "ok"},
        "estrutura_textual": {"nota": 6, "justificativa": "ok"},
        "coesao_coerencia": {"nota": 6, "justificativa": "ok"},
        "adequacao_ling": {"nota": 6, "justificativa": "ok"},
        "vocabulario": {"nota": 6, "justificativa": "ok"},
    }
    test_model = TestModel(custom_output_args={"scores": scores, "feedback": "ok", "sugestao_acionavel": "revise a introdução"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.validation_error is None
    assert response.structured is not None
    assert response.tokens_in > 0
    assert response.tokens_out > 0


@pytest.mark.asyncio
async def test_bedrock_provider_returns_validation_error_on_client_error():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")

    def raise_throttling(messages: list, info: AgentInfo):
        raise RuntimeError("ThrottlingException: Rate exceeded")

    with provider.agent.override(model=FunctionModel(raise_throttling)):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_bedrock_provider_returns_validation_error_on_incomplete_output():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    test_model = TestModel(custom_output_args={"scores": {}, "feedback": "ok", "sugestao_acionavel": "ok"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None


@pytest.mark.asyncio
async def test_bedrock_provider_splits_prefix_and_enables_instructions_caching():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    captured = {}

    def capture_call(messages: list, info: AgentInfo):
        captured["instructions"] = info.instructions
        captured["user_content"] = messages[-1].parts[-1].content
        captured["model_settings"] = info.model_settings
        raise RuntimeError("stop after capture")

    with provider.agent.override(model=FunctionModel(capture_call)):
        await provider.correct(essay_text="texto do aluno", prompt="Corrija: {essay_text}", params={"temperature": 0.1})

    # pydantic-ai's Agent.run strips the joined instructions string, so trailing whitespace
    # from the static prefix does not survive to AgentInfo.instructions (see test_openrouter_provider.py).
    assert captured["instructions"] == "Corrija:"
    assert captured["user_content"] == "texto do aluno"
    assert captured["model_settings"]["bedrock_cache_instructions"] is True
    assert captured["model_settings"]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_bedrock_provider_folds_cache_tokens_into_tokens_in():
    provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
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
