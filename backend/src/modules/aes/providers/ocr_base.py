from typing import Any, Protocol

from pydantic import BaseModel, Field


class OCRResult(BaseModel):
    text: str
    raw_response_ref: str | None = None
    transcricao_completa: bool = True
    trechos_ilegiveis: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class OCRProvider(Protocol):
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        ...
