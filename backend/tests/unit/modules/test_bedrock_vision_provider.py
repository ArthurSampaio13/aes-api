import pytest

from src.modules.aes.providers.bedrock_vision import BedrockVisionProvider

PDF_BYTES = b"%PDF-1.4 conteudo"
PNG_BYTES = b"\x89PNG\r\n\x1a\n conteudo"
JPEG_BYTES = b"\xff\xd8\xff\xe0 conteudo"


class FakeBedrockClient:
    def __init__(self) -> None:
        self.request: dict = {}

    async def converse(self, **kwargs):
        self.request = kwargs
        return {"output": {"message": {"content": [{"text": "Primeira linha.\nSegunda linha.\n"}]}}}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _provider() -> tuple[BedrockVisionProvider, FakeBedrockClient]:
    client = FakeBedrockClient()
    return BedrockVisionProvider(model_id="us.xai.grok-4.6", client_factory=lambda: client), client


@pytest.mark.asyncio
async def test_returns_the_transcription_stripped():
    provider, _ = _provider()
    result = await provider.extract_text(image_bytes=PNG_BYTES)
    assert result.text == "Primeira linha.\nSegunda linha."


@pytest.mark.asyncio
async def test_pdf_goes_as_a_document_block():
    """O Converse recusa PDF dentro de um bloco `image`; ele tem bloco proprio."""
    provider, client = _provider()
    await provider.extract_text(image_bytes=PDF_BYTES)
    block = client.request["messages"][0]["content"][0]
    assert block["document"]["format"] == "pdf"


@pytest.mark.asyncio
@pytest.mark.parametrize(("data", "expected"), [(PNG_BYTES, "png"), (JPEG_BYTES, "jpeg")])
async def test_image_format_comes_from_the_magic_bytes(data: bytes, expected: str):
    provider, client = _provider()
    await provider.extract_text(image_bytes=data)
    assert client.request["messages"][0]["content"][0]["image"]["format"] == expected


@pytest.mark.asyncio
async def test_prompt_forbids_fixing_the_student_spelling():
    """Corrigir a ortografia na transcricao falsearia o criterio adequacao_ling."""
    provider, client = _provider()
    await provider.extract_text(image_bytes=PNG_BYTES)
    prompt = client.request["messages"][0]["content"][1]["text"]
    assert "sem corrigir ortografia" in prompt


@pytest.mark.asyncio
async def test_uses_the_configured_model():
    provider, client = _provider()
    await provider.extract_text(image_bytes=PNG_BYTES)
    assert client.request["modelId"] == "us.xai.grok-4.6"
