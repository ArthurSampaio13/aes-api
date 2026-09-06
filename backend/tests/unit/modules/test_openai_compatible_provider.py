import pytest
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.openai_compatible import GATEWAY_BASE_URLS, OpenAICompatibleProvider

VALID_SCORES = {
    "adequacao_tema": {"nota": 7, "justificativa": "ok"},
    "estrutura_textual": {"nota": 7, "justificativa": "ok"},
    "coesao_coerencia": {"nota": 7, "justificativa": "ok"},
    "adequacao_ling": {"nota": 7, "justificativa": "ok"},
    "vocabulario": {"nota": 7, "justificativa": "ok"},
}


def _provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="test-key", model="some-model")


@pytest.mark.asyncio
async def test_parses_usage_and_content():
    provider = _provider()
    test_model = TestModel(
        custom_output_args={"scores": VALID_SCORES, "feedback": "ok", "sugestao_acionavel": "revise a conclusão"}
    )

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={"temperature": 0.0})

    assert response.validation_error is None
    assert response.structured is not None
    assert response.structured.sugestao_acionavel == "revise a conclusão"
    assert response.tokens_in > 0
    assert response.tokens_out > 0


@pytest.mark.asyncio
async def test_returns_validation_error_on_incomplete_output():
    provider = _provider()
    test_model = TestModel(custom_output_args={"scores": {}, "feedback": "ok", "sugestao_acionavel": "ok"})

    with provider.agent.override(model=test_model):
        response = await provider.correct(essay_text="texto", prompt="corrija: {essay_text}", params={})

    assert response.structured is None
    assert response.validation_error is not None
    assert response.validation_error_type is not None


def test_builds_without_an_api_key():
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="", model="some-model")

    assert provider.agent is not None


def test_every_gateway_preset_has_an_https_base_url():
    assert GATEWAY_BASE_URLS
    for name, base_url in GATEWAY_BASE_URLS.items():
        assert base_url.startswith("https://"), name
