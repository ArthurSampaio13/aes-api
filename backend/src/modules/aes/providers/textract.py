"""AWS Textract OCR provider — emulated locally by LocalStack, real Textract in production."""

from collections.abc import Callable
from typing import Any

import aioboto3

from .ocr_base import OCRResult


class TextractProvider:
    def __init__(self, client_factory: Callable[[], Any] | None = None) -> None:
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> Any:
        session = aioboto3.Session()
        return session.client("textract")

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        async with self._client_factory() as client:
            response = await client.detect_document_text(Document={"Bytes": image_bytes})
        lines = [block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"]
        return OCRResult(text="\n".join(lines))
