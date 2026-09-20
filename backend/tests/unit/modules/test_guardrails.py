from src.modules.aes.providers.base import FIXED_CRITERIA, CorrectionCandidate
from src.modules.aes.providers.guardrails import (
    CorrectionDeps,
    Transcription,
    contar_palavras,
    extrair_citacoes,
    guard_citacoes,
    guard_justificativas_distintas,
    guard_transcricao,
    normalizar,
)


def _ctx(deps):
    return type("Ctx", (), {"deps": deps})()


def _candidato(justificativas: list[str], feedback: str = "Bom texto.") -> CorrectionCandidate:
    scores = {c: {"nota": 7, "justificativa": j} for c, j in zip(FIXED_CRITERIA, justificativas)}
    return CorrectionCandidate.model_validate(
        {"scores": scores, "feedback": feedback, "sugestao_acionavel": "Revise o segundo paragrafo."}
    )


def test_contar_palavras_ignora_espaco_repetido_e_quebra_de_linha():
    assert contar_palavras("  uma   duas\n\ntres  ") == 3


def test_normalizar_remove_acento_caixa_e_espaco_repetido():
    assert normalizar("  A   CRIANÇA  brincou ") == "a crianca brincou"


def test_normalizar_troca_pontuacao_por_espaco():
    assert normalizar("caminhou, ate a escola") == "caminhou ate a escola"


def test_normalizar_nao_funde_palavras_separadas_so_por_pontuacao():
    assert normalizar("fim.Inicio") == "fim inicio"


def test_normalizar_nao_funde_palavras_separadas_por_pontuacao_tipografica():
    assert normalizar("fim—inicio") == "fim inicio"
    assert normalizar("fim–inicio") == "fim inicio"
    assert normalizar("fim‘inicio’") == "fim inicio"
    assert normalizar("fim…inicio") == "fim inicio"


def test_extrair_citacoes_pega_aspas_retas_e_tipograficas():
    texto = 'O aluno escreve "era uma vez" e tambem “foi muito bom”.'
    assert extrair_citacoes(texto) == ["era uma vez", "foi muito bom"]


def test_extrair_citacoes_ignora_trecho_curto_demais_para_ser_citacao():
    assert extrair_citacoes('usa "e" como conectivo') == []


def test_transcricao_incompleta_declarada_pelo_modelo_pede_retry():
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    log = []
    saida = Transcription(texto="a " * 100, transcricao_completa=False, trechos_ilegiveis=0)

    resultado = guard(_ctx(log), saida)

    assert resultado.action == "retry"
    assert log == [{"guard": "transcricao", "veredito": "retry", "motivo": "modelo declarou transcricao incompleta"}]


def test_transcricao_curta_reafirmada_como_completa_passa():
    """O caso que motivou a saida estruturada: aluno que escreveu pouco de
    verdade nao pode ser motivo para o modelo inventar texto."""
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    log = [{"guard": "transcricao", "veredito": "retry", "motivo": "poucas palavras: 3 abaixo de 40"}]
    saida = Transcription(texto="Eu gosto de jogar bola no recreio.", transcricao_completa=True, trechos_ilegiveis=0)

    resultado = guard(_ctx(log), saida)

    assert resultado.action == "allow"


def test_transcricao_vazia_pede_retry_mesmo_declarada_completa():
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    saida = Transcription(texto="   ", transcricao_completa=True, trechos_ilegiveis=0)

    assert guard(_ctx([]), saida).action == "retry"


def test_transcricao_so_de_pontuacao_pede_retry():
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    saida = Transcription(texto=" ... --- ,, ", transcricao_completa=True, trechos_ilegiveis=0)

    assert guard(_ctx([]), saida).action == "retry"


def test_transcricao_com_ilegivel_acima_da_razao_pede_retry():
    guard = guard_transcricao(min_palavras=10, max_ilegivel=0.2)
    saida = Transcription(
        texto="uma duas tres quatro cinco seis sete oito nove dez", transcricao_completa=True, trechos_ilegiveis=3
    )

    assert guard(_ctx([]), saida).action == "retry"


def test_transcricao_com_ilegivel_dentro_da_razao_passa():
    guard = guard_transcricao(min_palavras=10, max_ilegivel=0.2)
    saida = Transcription(
        texto="uma duas tres quatro cinco seis sete oito nove dez", transcricao_completa=True, trechos_ilegiveis=1
    )

    assert guard(_ctx([]), saida).action == "allow"


def test_transcricao_curta_pergunta_uma_vez_e_aceita_a_reafirmacao():
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    log = []
    saida = Transcription(texto="Eu gosto de jogar bola no recreio.", transcricao_completa=True, trechos_ilegiveis=0)

    primeira = guard(_ctx(log), saida)
    segunda = guard(_ctx(log), saida)

    assert primeira.action == "retry"
    assert segunda.action == "allow"
    assert [e["veredito"] for e in log] == ["retry", "allow"]


def test_transcricao_curta_reafirmada_mas_muito_ilegivel_continua_pedindo_retry():
    """A ilegibilidade tem que vencer mesmo quando a contagem de palavras ja foi reafirmada.

    Reproduz o buraco relatado: 10 palavras, 9 ilegiveis (razao 0.9 >> 0.2), reafirmada como
    completa apos um retry anterior por poucas palavras. Uma folha 90% ilegivel nao pode passar.
    """
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    log = [{"guard": "transcricao", "veredito": "retry", "motivo": "poucas palavras: 10 abaixo de 40"}]
    saida = Transcription(
        texto="uma duas tres quatro cinco seis sete oito nove dez", transcricao_completa=True, trechos_ilegiveis=9
    )

    assert guard(_ctx(log), saida).action == "retry"


def test_transcricao_vazia_continua_pedindo_retry_mesmo_apos_ja_ter_perguntado():
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    log = [{"guard": "transcricao", "veredito": "retry", "motivo": "poucas palavras: 0 abaixo de 40"}]
    saida = Transcription(texto="   ", transcricao_completa=True, trechos_ilegiveis=0)

    assert guard(_ctx(log), saida).action == "retry"


def test_retry_da_transcricao_pede_verificacao_e_nao_expansao():
    """A instrucao nao pode empurrar o modelo a escrever mais do que a folha tem."""
    guard = guard_transcricao(min_palavras=40, max_ilegivel=0.2)
    saida = Transcription(texto="tres palavras aqui", transcricao_completa=True, trechos_ilegiveis=0)

    instrucao = guard(_ctx([]), saida).message

    assert "confira" in instrucao.lower()
    assert "escreveu pouco" in instrucao.lower()


def test_citacao_ausente_da_redacao_pede_retry():
    deps = CorrectionDeps(essay_text="O menino foi a escola a pe.", events=[])
    candidato = _candidato(['O aluno escreve "correu pela floresta" sem conectivo.'] + ["ok"] * 4)

    resultado = guard_citacoes(_ctx(deps), candidato)

    assert resultado.action == "retry"
    assert "correu pela floresta" in resultado.message
    assert deps.events[0]["veredito"] == "retry"


def test_citacao_presente_na_redacao_passa_ignorando_acento_e_caixa():
    deps = CorrectionDeps(essay_text="O menino CORREU  pela  floresta.", events=[])
    candidato = _candidato(['O aluno escreve "correu pela floresta" bem.'] + ["ok"] * 4)

    assert guard_citacoes(_ctx(deps), candidato).action == "allow"


def test_citacao_no_feedback_tambem_e_verificada():
    deps = CorrectionDeps(essay_text="Texto simples do aluno.", events=[])
    candidato = _candidato(["ok"] * 5, feedback='Voce escreveu "jamais existiu isso" no final.')

    assert guard_citacoes(_ctx(deps), candidato).action == "retry"


def test_citacao_na_sugestao_acionavel_nao_pede_retry():
    """A sugestao acionavel existe para propor texto que o aluno ainda nao escreveu.

    Um guard que a trata como citacao de evidencia penaliza exatamente a sugestao pedagogica mais util (ex.: "use
    conectivos como 'portanto'"), que nunca vai aparecer literalmente na redacao do aluno.
    """
    deps = CorrectionDeps(essay_text="O menino foi a escola.", events=[])
    candidato = CorrectionCandidate.model_validate(
        {
            "scores": {c: {"nota": 7, "justificativa": "ok"} for c in FIXED_CRITERIA},
            "feedback": "Bom texto.",
            "sugestao_acionavel": 'Use conectivos como "portanto" para ligar as ideias.',
        }
    )

    assert guard_citacoes(_ctx(deps), candidato).action == "allow"


def test_citacao_que_so_difere_por_virgula_inserida_na_redacao_passa():
    deps = CorrectionDeps(essay_text="O menino caminhou, ate a escola.", events=[])
    candidato = _candidato(['O aluno escreve "caminhou ate a escola" com clareza.'] + ["ok"] * 4)

    assert guard_citacoes(_ctx(deps), candidato).action == "allow"


def test_citacao_genuinamente_ausente_continua_falhando_apos_ignorar_pontuacao():
    deps = CorrectionDeps(essay_text="O menino caminhou, ate a escola.", events=[])
    candidato = _candidato(['O aluno escreve "voou sobre a montanha" sem coesao.'] + ["ok"] * 4)

    assert guard_citacoes(_ctx(deps), candidato).action == "retry"


def test_justificativas_identicas_entre_criterios_pedem_retry():
    deps = CorrectionDeps(essay_text="qualquer", events=[])
    candidato = _candidato(["mesma justificativa"] * 5)

    resultado = guard_justificativas_distintas(_ctx(deps), candidato)

    assert resultado.action == "retry"


def test_justificativas_distintas_passam():
    deps = CorrectionDeps(essay_text="qualquer", events=[])
    candidato = _candidato(["um", "dois", "tres", "quatro", "cinco"])

    assert guard_justificativas_distintas(_ctx(deps), candidato).action == "allow"
