import pytest
from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.modules.aes.providers.vision import TRANSCRIPTION_PROMPT, VisionOCRProvider


def test_construction_succeeds_without_the_key_in_the_process_environment(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")
    assert provider.model_id == "openrouter:modelo/teste"


PDF_BYTES = b"%PDF-1.4 conteudo"
PNG_BYTES = b"\x89PNG\r\n\x1a\n conteudo"
JPEG_BYTES = b"\xff\xd8\xff\xe0 conteudo"


def _capturing_model(capturado: dict):
    def responder(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        capturado["messages"] = messages
        capturado["settings"] = info.model_settings
        return ModelResponse(parts=[TextPart("  Primeira linha.\nSegunda linha.\n")])

    return FunctionModel(responder)


def _partes_do_pedido(capturado: dict) -> list:
    partes = []
    for message in capturado["messages"]:
        for part in getattr(message, "parts", []):
            conteudo = getattr(part, "content", None)
            if isinstance(conteudo, list):
                partes += conteudo
    return partes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "media_type"),
    [(PDF_BYTES, "application/pdf"), (PNG_BYTES, "image/png"), (JPEG_BYTES, "image/jpeg")],
)
async def test_media_type_comes_from_the_magic_bytes(data: bytes, media_type: str):
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=data)

    binarias = [p for p in _partes_do_pedido(capturado) if isinstance(p, BinaryContent)]
    assert len(binarias) == 1
    assert binarias[0].media_type == media_type
    assert binarias[0].data == data


@pytest.mark.asyncio
async def test_returns_the_transcription_stripped():
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model({})):
        result = await provider.extract_text(image_bytes=PNG_BYTES)

    assert result.text == "Primeira linha.\nSegunda linha."


@pytest.mark.asyncio
async def test_the_prompt_that_reaches_the_model_forbids_fixing_the_student_spelling():
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=PNG_BYTES)

    assert TRANSCRIPTION_PROMPT in _partes_do_pedido(capturado)
    assert "sem corrigir ortografia" in TRANSCRIPTION_PROMPT


@pytest.mark.asyncio
async def test_transcription_is_deterministic_and_denies_provider_data_collection():
    capturado: dict = {}
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model(capturado)):
        await provider.extract_text(image_bytes=PNG_BYTES)

    assert capturado["settings"]["temperature"] == 0.0
    assert capturado["settings"]["openrouter_provider"]["data_collection"] == "deny"
    assert capturado["settings"]["seed"] == 42
