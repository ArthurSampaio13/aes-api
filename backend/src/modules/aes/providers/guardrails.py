"""Guards determinísticos aplicados às saídas dos modelos.

Funções puras, construídas por fábrica com limiares explícitos: os testes passam os números, e o provider os lê das
settings. São reusadas como métrica offline na avaliação científica.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypedDict

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai_harness import GuardrailResult

from .base import CorrectionCandidate


class GuardrailEvent(TypedDict):
    guard: str
    veredito: str
    motivo: str


GuardrailLog = list[GuardrailEvent]


class Transcription(BaseModel):
    texto: str
    transcricao_completa: bool
    trechos_ilegiveis: int = Field(ge=0)


@dataclass
class CorrectionDeps:
    essay_text: str
    events: GuardrailLog = field(default_factory=list)


_PALAVRA = re.compile(r"\w+", re.UNICODE)
_CITACAO = re.compile(r"[\"“„«]([^\"“”«»]{4,})[\"”»]")
_PONTUACAO = re.compile(r"[^\w\s]", re.UNICODE)


def contar_palavras(texto: str) -> int:
    return len(_PALAVRA.findall(texto))


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    sem_pontuacao = _PONTUACAO.sub(" ", sem_acento)
    return re.sub(r"\s+", " ", sem_pontuacao).casefold().strip()


def extrair_citacoes(texto: str) -> list[str]:
    return [m.group(1).strip() for m in _CITACAO.finditer(texto)]


def _registrar(events: GuardrailLog, guard: str, veredito: str, motivo: str) -> None:
    events.append({"guard": guard, "veredito": veredito, "motivo": motivo})


_RETRY_TRANSCRICAO = (
    "Confira se restou texto na folha que não entrou na transcrição. "
    "Se o aluno realmente escreveu pouco, repita exatamente a mesma transcrição "
    "e mantenha transcricao_completa=True. Não acrescente texto que não está na imagem."
)

_MOTIVO_POUCAS = "poucas palavras"


def guard_transcricao(
    min_palavras: int, max_ilegivel: float
) -> Callable[[RunContext[GuardrailLog], Transcription], GuardrailResult]:
    def guard(ctx: RunContext[GuardrailLog], output: Transcription) -> GuardrailResult:
        if not output.transcricao_completa:
            _registrar(ctx.deps, "transcricao", "retry", "modelo declarou transcricao incompleta")
            return GuardrailResult.retry(_RETRY_TRANSCRICAO)

        palavras = contar_palavras(output.texto)
        if palavras == 0:
            _registrar(ctx.deps, "transcricao", "retry", "transcricao vazia ou sem palavras")
            return GuardrailResult.retry(_RETRY_TRANSCRICAO)

        if palavras < min_palavras:
            ja_perguntou = any(e["guard"] == "transcricao" and e["motivo"].startswith(_MOTIVO_POUCAS) for e in ctx.deps)
            if not ja_perguntou:
                _registrar(ctx.deps, "transcricao", "retry", f"{_MOTIVO_POUCAS}: {palavras} abaixo de {min_palavras}")
                return GuardrailResult.retry(_RETRY_TRANSCRICAO)
            _registrar(ctx.deps, "transcricao", "allow", f"{palavras} palavras reafirmadas como completas")
            return GuardrailResult.allow()

        if output.trechos_ilegiveis / palavras > max_ilegivel:
            _registrar(ctx.deps, "transcricao", "retry", f"{output.trechos_ilegiveis} trechos ilegiveis em {palavras} palavras")
            return GuardrailResult.retry(_RETRY_TRANSCRICAO)

        _registrar(ctx.deps, "transcricao", "allow", f"{palavras} palavras")
        return GuardrailResult.allow()

    return guard


def _textos_avaliativos(output: CorrectionCandidate) -> list[str]:
    scores = output.scores.model_dump()
    return [c["justificativa"] for c in scores.values()] + [output.feedback, output.sugestao_acionavel]


def guard_citacoes(ctx: RunContext[CorrectionDeps], output: CorrectionCandidate) -> GuardrailResult:
    redacao = normalizar(ctx.deps.essay_text)
    for texto in _textos_avaliativos(output):
        for citacao in extrair_citacoes(texto):
            if normalizar(citacao) not in redacao:
                _registrar(ctx.deps.events, "citacoes", "retry", f"citacao ausente: {citacao}")
                return GuardrailResult.retry(
                    f'A justificativa cita "{citacao}", que não aparece na redação do aluno. '
                    "Cite apenas trechos presentes no texto, ou reescreva sem citar."
                )
    _registrar(ctx.deps.events, "citacoes", "allow", "todas as citacoes ancoradas")
    return GuardrailResult.allow()


def guard_justificativas_distintas(ctx: RunContext[CorrectionDeps], output: CorrectionCandidate) -> GuardrailResult:
    justificativas = [normalizar(c["justificativa"]) for c in output.scores.model_dump().values()]
    repetidas = len(justificativas) - len(set(justificativas))
    if repetidas:
        _registrar(ctx.deps.events, "justificativas", "retry", f"{repetidas} justificativas repetidas")
        return GuardrailResult.retry(
            "Há justificativas idênticas entre critérios diferentes. "
            "Cada critério precisa de uma justificativa própria, baseada em evidência do texto."
        )
    _registrar(ctx.deps.events, "justificativas", "allow", "justificativas distintas")
    return GuardrailResult.allow()
