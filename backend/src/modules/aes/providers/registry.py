"""Maps a CorrectionJob.provider string to a real CorrectionProvider instance."""

from collections.abc import Callable

from ....infrastructure.config.settings import get_settings
from .base import CorrectionProvider
from .bedrock import BedrockProvider
from .bedrock_vision import BedrockVisionProvider
from .mock import MockProvider
from .mock_ocr import MockOCRProvider
from .ocr_base import OCRProvider
from .openai_compatible import GATEWAY_BASE_URLS, OpenAICompatibleProvider
from .openrouter import OpenRouterProvider
from .textract import TextractProvider

_settings = get_settings()

PROVIDER_FACTORIES: dict[str, Callable[[], CorrectionProvider]] = {
    "mock": lambda: MockProvider(),
    "openrouter": lambda: OpenRouterProvider(api_key=_settings.OPENROUTER_API_KEY or "", model=_settings.OPENROUTER_MODEL),
    "bedrock": lambda: BedrockProvider(model_id=_settings.BEDROCK_MODEL_ID),
}


def _gateway_factory(name: str, base_url: str) -> Callable[[], CorrectionProvider]:
    def build() -> CorrectionProvider:
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=getattr(_settings, f"{name.upper()}_API_KEY", None) or "",
            model=getattr(_settings, f"{name.upper()}_MODEL"),
        )

    return build


PROVIDER_FACTORIES.update({name: _gateway_factory(name, base_url) for name, base_url in GATEWAY_BASE_URLS.items()})

OCR_PROVIDER_FACTORIES: dict[str, Callable[[], OCRProvider]] = {
    "mock": lambda: MockOCRProvider(),
    "textract": lambda: TextractProvider(),
    "bedrock_vision": lambda: BedrockVisionProvider(model_id=_settings.AES_VISION_MODEL_ID),
}


def get_provider(name: str) -> CorrectionProvider:
    return PROVIDER_FACTORIES[name]()


def get_ocr_provider(name: str) -> OCRProvider:
    return OCR_PROVIDER_FACTORIES[name]()
