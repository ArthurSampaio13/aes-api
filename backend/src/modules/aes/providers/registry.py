"""Maps a CorrectionJob.provider string to a real CorrectionProvider instance."""

from collections.abc import Callable

from ....infrastructure.config.settings import get_settings
from .base import CorrectionProvider
from .bedrock import BedrockProvider
from .mock import MockProvider
from .openrouter import OpenRouterProvider

_settings = get_settings()

PROVIDER_FACTORIES: dict[str, Callable[[], CorrectionProvider]] = {
    "mock": lambda: MockProvider(),
    "openrouter": lambda: OpenRouterProvider(api_key=_settings.OPENROUTER_API_KEY or "", model=_settings.OPENROUTER_MODEL),
    "bedrock": lambda: BedrockProvider(model_id=_settings.BEDROCK_MODEL_ID),
}


def get_provider(name: str) -> CorrectionProvider:
    return PROVIDER_FACTORIES[name]()
