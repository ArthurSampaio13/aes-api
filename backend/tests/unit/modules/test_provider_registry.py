import pytest

from src.modules.aes.providers.llm import LLMCorrectionProvider
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.providers.registry import agent_model_id, get_ocr_provider, get_provider, resolve_model
from src.modules.aes.providers.vision import VisionOCRProvider


def test_resolve_model_stays_bare():
    assert resolve_model("openrouter", "deepseek/deepseek-v4.1-flash") == "deepseek/deepseek-v4.1-flash"


def test_resolve_model_leaves_mock_alone():
    assert resolve_model("mock", None) == "mock"


def test_agent_model_id_prefixes_with_the_router():
    assert agent_model_id("openrouter", "deepseek/deepseek-v4.1-flash") == "openrouter:deepseek/deepseek-v4.1-flash"


def test_openrouter_builds_the_unified_provider():
    provider = get_provider("openrouter", "deepseek/deepseek-v4.1-flash")
    assert isinstance(provider, LLMCorrectionProvider)
    assert provider.model_id == "openrouter:deepseek/deepseek-v4.1-flash"


def test_mock_stays_offline():
    assert isinstance(get_provider("mock"), MockProvider)


def test_vision_ocr_is_registered():
    assert isinstance(get_ocr_provider("vision"), VisionOCRProvider)


def test_mock_ocr_stays_offline():
    assert isinstance(get_ocr_provider("mock"), MockOCRProvider)


@pytest.mark.parametrize("removido", ["bedrock", "groq", "cerebras", "github", "gemini"])
def test_retired_providers_are_gone(removido: str):
    with pytest.raises(KeyError):
        get_provider(removido)


@pytest.mark.parametrize("removido", ["textract", "bedrock_vision"])
def test_retired_ocr_providers_are_gone(removido: str):
    with pytest.raises(KeyError):
        get_ocr_provider(removido)
