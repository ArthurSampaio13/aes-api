"""Transcrição de manuscrito por modelo multimodal.

O Textract reconhece manuscrito apenas em inglês, então redação em português sai ilegível por ele. Um modelo multimodal
não tem essa restrição de idioma.
"""

from pydantic_ai import Agent, BinaryContent

from ._pydantic_ai_support import openrouter_model_settings, resolve_agent_model
from .ocr_base import OCRResult

TRANSCRIPTION_PROMPT = """Transcreva exatamente o texto manuscrito desta redação escolar.

Regras:
- Copie o texto como está escrito, sem corrigir ortografia, acentuação, concordância ou pontuação.
- Preserve a divisão em parágrafos e a quebra de linhas.
- Não acrescente comentários, títulos ou explicações suas.
- Se um trecho estiver ilegível, escreva [ilegível] no lugar.

Responda apenas com a transcrição."""


def _media_type(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"


class VisionOCRProvider:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.agent = Agent(resolve_agent_model(model_id), output_type=str)

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        result = await self.agent.run(  # type: ignore[call-overload]
            [TRANSCRIPTION_PROMPT, BinaryContent(data=image_bytes, media_type=_media_type(image_bytes))],
            model_settings=openrouter_model_settings(0.0),
        )
        return OCRResult(text=result.output.strip())
