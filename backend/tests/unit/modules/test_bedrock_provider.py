import pytest
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
