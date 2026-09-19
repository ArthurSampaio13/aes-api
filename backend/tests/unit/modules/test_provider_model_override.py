"""O modelo vem do job, não das settings.

A rota sempre aceitou `model` e o gravava no banco, mas quem executava era o
registry, montado a partir das settings — a tentativa registrava um modelo que
não foi usado.
"""

import pytest

from src.infrastructure.config.settings import get_settings
from src.modules.aes.providers.registry import get_provider

OUTRO_MODELO = "deepseek/deepseek-v4.1-flash"


def test_openrouter_uses_the_model_from_the_job() -> None:
    assert get_provider("openrouter", OUTRO_MODELO).model_id == OUTRO_MODELO


def test_bedrock_uses_the_model_from_the_job() -> None:
    assert get_provider("bedrock", OUTRO_MODELO).model_id == OUTRO_MODELO


def test_gateway_uses_the_model_from_the_job() -> None:
    assert get_provider("groq", OUTRO_MODELO).model_id == OUTRO_MODELO


@pytest.mark.parametrize("name", ["openrouter", "bedrock", "groq"])
def test_omitting_the_model_falls_back_to_the_configured_default(name: str) -> None:
    settings = get_settings()
    esperado = {
        "openrouter": settings.OPENROUTER_MODEL,
        "bedrock": settings.BEDROCK_MODEL_ID,
        "groq": settings.GROQ_MODEL,
    }[name]
    assert get_provider(name).model_id == esperado


def test_mock_ignores_the_model() -> None:
    assert get_provider("mock", OUTRO_MODELO) is not None
