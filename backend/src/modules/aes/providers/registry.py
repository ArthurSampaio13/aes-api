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


def default_model(name: str) -> str:
    fixed = {"mock": "mock", "openrouter": _settings.OPENROUTER_MODEL, "bedrock": _settings.BEDROCK_MODEL_ID}
    return fixed.get(name) or str(getattr(_settings, f"{name.upper()}_MODEL"))


def resolve_model(name: str, model: str | None) -> str:
    """O modelo efetivo, sem construir o provider.

    A submissão precisa gravar um modelo concreto no job antes de existir provider algum, e a tentativa precisa do mesmo
    valor depois — daí a resolução viver aqui, e não dentro de cada factory.
    """
    return model or default_model(name)


PROVIDER_FACTORIES: dict[str, Callable[[str | None], CorrectionProvider]] = {
    "mock": lambda model: MockProvider(),
    "openrouter": lambda model: OpenRouterProvider(
        api_key=_settings.OPENROUTER_API_KEY or "", model=resolve_model("openrouter", model)
    ),
    "bedrock": lambda model: BedrockProvider(model_id=resolve_model("bedrock", model)),
}


def _gateway_factory(name: str, base_url: str) -> Callable[[str | None], CorrectionProvider]:
    def build(model: str | None) -> CorrectionProvider:
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=getattr(_settings, f"{name.upper()}_API_KEY", None) or "",
            model=resolve_model(name, model),
        )

    return build


PROVIDER_FACTORIES.update({name: _gateway_factory(name, base_url) for name, base_url in GATEWAY_BASE_URLS.items()})

OCR_PROVIDER_FACTORIES: dict[str, Callable[[], OCRProvider]] = {
    "mock": lambda: MockOCRProvider(),
    "textract": lambda: TextractProvider(),
    "bedrock_vision": lambda: BedrockVisionProvider(model_id=_settings.AES_VISION_MODEL_ID),
}


def get_provider(name: str, model: str | None = None) -> CorrectionProvider:
    """`model` vem da requisição; None cai no default configurado do provider.

    Um id inválido não é validado aqui: o catálogo do OpenRouter é grande e muda, e checar custaria uma chamada por job.
    A falha aparece no provider e fica registrada verbatim no request/response gravados da tentativa.
    """
    return PROVIDER_FACTORIES[name](model)


def get_ocr_provider(name: str) -> OCRProvider:
    return OCR_PROVIDER_FACTORIES[name]()
