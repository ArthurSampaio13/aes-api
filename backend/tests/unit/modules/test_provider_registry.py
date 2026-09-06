import pytest

from src.modules.aes.providers.bedrock import BedrockProvider
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.providers.openai_compatible import GATEWAY_BASE_URLS, OpenAICompatibleProvider
from src.modules.aes.providers.openrouter import OpenRouterProvider
from src.modules.aes.providers.registry import PROVIDER_FACTORIES, get_ocr_provider, get_provider
from src.modules.aes.providers.textract import TextractProvider


def test_get_provider_returns_mock_for_mock_name():
    provider = get_provider("mock")
    assert isinstance(provider, MockProvider)


def test_get_provider_returns_openrouter_for_openrouter_name():
    provider = get_provider("openrouter")
    assert isinstance(provider, OpenRouterProvider)


def test_get_provider_returns_bedrock_for_bedrock_name():
    provider = get_provider("bedrock")
    assert isinstance(provider, BedrockProvider)


def test_get_provider_raises_key_error_for_unknown_name():
    with pytest.raises(KeyError):
        get_provider("does-not-exist")


def test_get_ocr_provider_returns_mock_for_mock_name():
    provider = get_ocr_provider("mock")
    assert isinstance(provider, MockOCRProvider)


def test_get_ocr_provider_returns_textract_for_textract_name():
    provider = get_ocr_provider("textract")
    assert isinstance(provider, TextractProvider)


def test_get_ocr_provider_raises_key_error_for_unknown_name():
    with pytest.raises(KeyError):
        get_ocr_provider("does-not-exist")


def test_registry_exposes_every_gateway_preset():
    for name in GATEWAY_BASE_URLS:
        assert name in PROVIDER_FACTORIES, name


def test_gateway_providers_are_built_with_their_preset_base_url():
    for name, base_url in GATEWAY_BASE_URLS.items():
        provider = get_provider(name)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.base_url == base_url
