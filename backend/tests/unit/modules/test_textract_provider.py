import pytest

from src.modules.aes.providers.textract import TextractProvider


class FakeTextractClient:
    async def detect_document_text(self, Document):
        return {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Primeira linha da redação."},
                {"BlockType": "LINE", "Text": "Segunda linha da redação."},
                {"BlockType": "WORD", "Text": "ignorado"},
            ]
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_textract_provider_joins_line_blocks_only():
    provider = TextractProvider(client_factory=lambda: FakeTextractClient())
    result = await provider.extract_text(image_bytes=b"fake-bytes")
    assert result.text == "Primeira linha da redação.\nSegunda linha da redação."
