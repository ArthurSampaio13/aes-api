import pytest
from pydantic_ai.models.test import TestModel

from src.modules.aes.providers.base import FIXED_CRITERIA
from src.modules.aes.providers.llm import LLMCorrectionProvider

VALID_SCORES = {c: {"nota": 7, "justificativa": "ok"} for c in FIXED_CRITERIA}


@pytest.fixture(autouse=True)
def _set_openrouter_api_key_for_infer_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-for-provider-tests")


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
