from .ocr_base import OCRResult


class MockOCRProvider:
    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(
            text="Transcrição simulada da redação do aluno para fins de teste automatizado.",
            transcricao_completa=True,
            trechos_ilegiveis=0,
            meta={"model": "mock", "model_retries": 0, "guardrail_events": []},
        )
