import pytest

from src.modules.aes.providers.bedrock import BedrockProvider
from src.modules.aes.providers.mock import MockProvider
from src.modules.aes.providers.mock_ocr import MockOCRProvider
from src.modules.aes.providers.openrouter import OpenRouterProvider
from src.modules.aes.providers.registry import get_ocr_provider, get_provider
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
