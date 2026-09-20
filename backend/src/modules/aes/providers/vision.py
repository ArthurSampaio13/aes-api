"""Transcrição de manuscrito por modelo multimodal.

O Textract reconhece manuscrito apenas em inglês, então redação em português sai ilegível por ele. Um modelo multimodal
não tem essa restrição de idioma.

A saída é estruturada, e não texto puro, porque o guardrail precisa separar "o modelo pegou só um pedaço da folha" de "o
aluno escreveu pouco". Sem essa distinção, o retry pressiona o modelo a inventar texto.
"""

import time

from pydantic_ai import Agent, BinaryContent, capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai_harness import OutputGuardrail

from ....infrastructure.config.settings import get_settings
from ...common.exceptions import TranscriptionQualityError
from ._pydantic_ai_support import (
    contar_respostas_do_modelo,
    custo_e_origem,
    dump_exchange,
    openrouter_model_settings,
    provedor_servido,
    resolve_agent_model,
    somar_uso_do_modelo,
)
from .guardrails import GuardrailLog, Transcription, contar_palavras, guard_transcricao
from .ocr_base import OCRResult

TRANSCRIPTION_PROMPT = """Transcreva exatamente o texto manuscrito desta redação escolar.

Regras:
- Copie o texto como está escrito, sem corrigir ortografia, acentuação, concordância ou pontuação.
- Preserve a divisão em parágrafos e a quebra de linhas.
- Não acrescente comentários, títulos ou explicações suas.
- Se um trecho estiver ilegível, escreva [ilegível] no lugar e conte-o em trechos_ilegiveis.
- Preencha transcricao_completa com true apenas se você transcreveu a folha inteira, do começo ao fim.

Responda apenas com a transcrição."""


def _media_type(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"


class VisionOCRProvider:
    def __init__(self, model_id: str) -> None:
        settings = get_settings()
        self.model_id = model_id
        guardrail = OutputGuardrail[GuardrailLog](
            guard=guard_transcricao(  # type: ignore[arg-type]
                min_palavras=settings.AES_OCR_MIN_WORDS,
                max_ilegivel=settings.AES_OCR_MAX_ILLEGIBLE_RATIO,
            )
        )
        self.agent = Agent(
            resolve_agent_model(model_id),
            output_type=Transcription,
            deps_type=GuardrailLog,
            retries={"output": settings.AES_OCR_MAX_RETRIES},
            capabilities=[guardrail],
        )

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        eventos: GuardrailLog = []
        started_at = time.monotonic()

        with capture_run_messages() as exchange:
            try:
                result = await self.agent.run(  # type: ignore[call-overload]
                    [TRANSCRIPTION_PROMPT, BinaryContent(data=image_bytes, media_type=_media_type(image_bytes))],
                    model_settings=openrouter_model_settings(0.0),
                    deps=eventos,
                )
            except Exception as exc:
                uso = somar_uso_do_modelo(exchange)
                custo, origem = custo_e_origem(exchange, uso.cost_usd)
                partial_meta = {
                    "model": self.model_id,
                    "tokens_in": uso.tokens_in,
                    "tokens_out": uso.tokens_out,
                    "cache_read_tokens": uso.cache_read_tokens,
                    "cache_write_tokens": uso.cache_write_tokens,
                    "cost_usd": str(custo) if custo is not None else None,
                    "cost_source": origem,
                    "served_provider": provedor_servido(exchange),
                    "latency_ms": int((time.monotonic() - started_at) * 1000),
                    "model_retries": max(contar_respostas_do_modelo(exchange) - 1, 0),
                    "guardrail_events": eventos,
                    "raw_exchange": dump_exchange(exchange),
                }
                if isinstance(exc, UnexpectedModelBehavior):
                    raise TranscriptionQualityError(
                        f"Transcrição insuficiente após {get_settings().AES_OCR_MAX_RETRIES} tentativas; "
                        "a folha requer digitação manual.",
                        partial_meta=partial_meta,
                    ) from exc
                exc.partial_meta = partial_meta  # type: ignore[attr-defined]
                raise

        texto = result.output.texto.strip()
        usage = result.usage
        custo, origem = custo_e_origem(exchange, usage.cost)
        return OCRResult(
            text=texto,
            transcricao_completa=result.output.transcricao_completa,
            trechos_ilegiveis=result.output.trechos_ilegiveis,
            meta={
                "model": self.model_id,
                "tokens_in": usage.input_tokens,
                "tokens_out": usage.output_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_write_tokens": usage.cache_write_tokens,
                "cost_usd": str(custo) if custo is not None else None,
                "cost_source": origem,
                "served_provider": provedor_servido(exchange),
                "latency_ms": int((time.monotonic() - started_at) * 1000),
                "model_retries": max(contar_respostas_do_modelo(exchange) - 1, 0),
                "guardrail_events": eventos,
                "palavras": contar_palavras(texto),
                "transcricao_completa": result.output.transcricao_completa,
                "trechos_ilegiveis": result.output.trechos_ilegiveis,
                "raw_exchange": dump_exchange(exchange),
            },
        )
