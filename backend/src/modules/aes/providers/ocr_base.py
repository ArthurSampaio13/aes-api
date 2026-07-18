from typing import Protocol

from pydantic import BaseModel


class OCRResult(BaseModel):
    text: str
    raw_response_ref: str | None = None


class OCRProvider(Protocol):
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        ...
