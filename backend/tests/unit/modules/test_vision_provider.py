import pytest
from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.modules.aes.providers.vision import TRANSCRIPTION_PROMPT, VisionOCRProvider


@pytest.fixture(autouse=True)
def _set_openrouter_api_key_for_infer_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-for-provider-tests")


PDF_BYTES = b"%PDF-1.4 conteudo"
PNG_BYTES = b"\x89PNG\r\n\x1a\n conteudo"
JPEG_BYTES = b"\xff\xd8\xff\xe0 conteudo"


def _capturing_model(capturado: dict):
    def responder(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        capturado["messages"] = messages
        return ModelResponse(parts=[TextPart("Primeira linha.\nSegunda linha.")])

    return FunctionModel(responder)


def _partes_binarias(capturado: dict) -> list[BinaryContent]:
    partes = []
    for message in capturado["messages"]:
        for part in getattr(message, "parts", []):
            conteudo = getattr(part, "content", None)
            if isinstance(conteudo, list):
                partes += [c for c in conteudo if isinstance(c, BinaryContent)]
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

    binarias = _partes_binarias(capturado)
    assert len(binarias) == 1
    assert binarias[0].media_type == media_type
    assert binarias[0].data == data


@pytest.mark.asyncio
async def test_returns_the_transcription_stripped():
    provider = VisionOCRProvider(model_id="openrouter:modelo/teste")

    with provider.agent.override(model=_capturing_model({})):
        result = await provider.extract_text(image_bytes=PNG_BYTES)

    assert result.text == "Primeira linha.\nSegunda linha."


def test_prompt_forbids_fixing_the_student_spelling():
    assert "sem corrigir ortografia" in TRANSCRIPTION_PROMPT
