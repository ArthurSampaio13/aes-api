"""O modelo vem do job, não das settings.

A rota sempre aceitou `model` e o gravava no banco, mas quem executava era o
registry, montado a partir das settings — a tentativa registrava um modelo que
não foi usado.
"""

from src.infrastructure.config.settings import get_settings
from src.modules.aes.providers.registry import get_provider

OUTRO_MODELO = "deepseek/deepseek-v4.1-flash"


def test_openrouter_uses_the_model_from_the_job() -> None:
    assert get_provider("openrouter", OUTRO_MODELO).model_id == f"openrouter:{OUTRO_MODELO}"


def test_omitting_the_model_falls_back_to_the_configured_default() -> None:
    settings = get_settings()
    assert get_provider("openrouter").model_id == f"openrouter:{settings.OPENROUTER_MODEL}"


def test_mock_ignores_the_model() -> None:
    assert get_provider("mock", OUTRO_MODELO) is not None
