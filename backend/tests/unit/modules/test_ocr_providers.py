import pytest

from src.modules.aes.providers.mock_ocr import MockOCRProvider


@pytest.mark.asyncio
async def test_mock_ocr_returns_nonempty_text():
    provider = MockOCRProvider()
    result = await provider.extract_text(image_bytes=b"fake-image-bytes")
    assert len(result.text) > 0
