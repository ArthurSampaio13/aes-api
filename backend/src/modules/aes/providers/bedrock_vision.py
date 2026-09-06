"""Transcricao por modelo multimodal no Bedrock, para manuscrito fora do ingles.

O Textract reconhece manuscrito apenas em ingles, entao redacao em portugues sai ilegivel por ele. Um modelo multimodal
le a imagem direto e nao tem essa restricao de idioma.
"""

from collections.abc import Callable
from typing import Any

import aioboto3

from .ocr_base import OCRResult

# A transcricao alimenta uma correcao que avalia adequacao a norma escrita. Se o
# modelo "arrumar" a ortografia do aluno, o criterio avalia o texto do modelo, e
# nao o do aluno — por isso a instrucao de preservar o erro e tao enfatica.
TRANSCRIPTION_PROMPT = """Transcreva exatamente o texto manuscrito desta redação escolar.

Regras:
- Copie o texto como está escrito, sem corrigir ortografia, acentuação, concordância ou pontuação.
- Preserve a divisão em parágrafos e a quebra de linhas.
- Não acrescente comentários, títulos ou explicações suas.
- Se um trecho estiver ilegível, escreva [ilegível] no lugar.

Responda apenas com a transcrição."""


class BedrockVisionProvider:
    def __init__(self, model_id: str, client_factory: Callable[[], Any] | None = None) -> None:
        self._model_id = model_id
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> Any:
        session = aioboto3.Session()
        return session.client("bedrock-runtime")

    @staticmethod
    def _content_block(image_bytes: bytes) -> dict[str, Any]:
        """PDF vai como `document`; imagem vai como `image`.

        O Converse separa os dois.
        """
        if image_bytes.startswith(b"%PDF"):
            return {"document": {"format": "pdf", "name": "redacao", "source": {"bytes": image_bytes}}}
        image_format = "png" if image_bytes.startswith(b"\x89PNG") else "jpeg"
        return {"image": {"format": image_format, "source": {"bytes": image_bytes}}}

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        async with self._client_factory() as client:
            response = await client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [self._content_block(image_bytes), {"text": TRANSCRIPTION_PROMPT}],
                    }
                ],
                inferenceConfig={"temperature": 0.0},
            )

        parts = [block["text"] for block in response["output"]["message"]["content"] if "text" in block]
        return OCRResult(text="\n".join(parts).strip())
