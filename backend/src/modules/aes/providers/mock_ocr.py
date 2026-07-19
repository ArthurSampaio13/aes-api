from .ocr_base import OCRResult


class MockOCRProvider:
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(text="[transcrição simulada da imagem enviada]", raw_response_ref=None)
