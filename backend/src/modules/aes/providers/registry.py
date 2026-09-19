"""Mapeia o provider do job para um CorrectionProvider ou OCRProvider real."""

from collections.abc import Callable

from ....infrastructure.config.settings import get_settings
from .base import CorrectionProvider
from .llm import LLMCorrectionProvider
from .mock import MockProvider
from .mock_ocr import MockOCRProvider
from .ocr_base import OCRProvider
from .vision import VisionOCRProvider

_settings = get_settings()

ROUTER_PREFIX = "openrouter"
DEFAULT_OPENROUTER_MODEL = _settings.OPENROUTER_MODEL


def resolve_model(name: str, model: str | None) -> str:
    """O modelo efetivo, sem prefixo — o que fica gravado em CorrectionJob.model e CorrectionAttempt.model."""
    if name == "mock":
        return "mock"
    return model or DEFAULT_OPENROUTER_MODEL


def agent_model_id(name: str, model: str | None) -> str:
    """O identificador prefixado que `infer_model` da pydantic-ai resolve."""
    return f"{name}:{resolve_model(name, model)}"


PROVIDER_FACTORIES: dict[str, Callable[[str | None], CorrectionProvider]] = {
    "mock": lambda model: MockProvider(),
    ROUTER_PREFIX: lambda model: LLMCorrectionProvider(model_id=agent_model_id(ROUTER_PREFIX, model)),
}

OCR_PROVIDER_FACTORIES: dict[str, Callable[[], OCRProvider]] = {
    "mock": lambda: MockOCRProvider(),
    "vision": lambda: VisionOCRProvider(model_id=agent_model_id(ROUTER_PREFIX, _settings.AES_VISION_MODEL)),
}


def get_provider(name: str, model: str | None = None) -> CorrectionProvider:
    return PROVIDER_FACTORIES[name](model)


def get_ocr_provider(name: str) -> OCRProvider:
    return OCR_PROVIDER_FACTORIES[name]()
