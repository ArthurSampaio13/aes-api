#!/usr/bin/env python3
"""Confiabilidade teste-reteste das notas de um lote corrigido k vezes.

    scripts/analise-teste-reteste.py <manifesto.json|notas.csv> [outro ...]
    scripts/analise-teste-reteste.py --autoteste

Vários manifestos são agrupados num conjunto só: cada redação entra pelo rótulo, que já
é único entre turmas (9A-01, 9B-01...). Agrupar é o que leva o n acima das 30 amostras
que Koo e Li pedem.

Mede a estabilidade do sistema consigo mesmo sob reexecução. Não mede acerto: sem
nota humana de referência, nenhum número aqui autoriza dizer que as notas estão certas.

ICC(2,1) de duas vias, concordância absoluta, medida única — o coeficiente que Koo e Li
recomendam quando as execuções são amostras de uma população de execuções possíveis e
interessa o valor absoluto da nota, não só a ordenação. O intervalo é de bootstrap
percentil sobre as redações, e não a fórmula analítica com F: a analítica assume
normalidade, e nota de rubrica 0-10 é ordinal e truncada.

Sem dependência externa de propósito: roda com o python3 do sistema.
"""

import pathlib
import random
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from _dados import carregar  # noqa: E402

BOOTSTRAP = 2000
SEMENTE = 20260920


def icc21(matriz: list[list[float]]) -> float | None:
    """ICC(2,1): duas vias, efeitos aleatórios, concordância absoluta, medida única.

    matriz[i][j] = nota da redação i na execução j. Devolve None quando o desenho é pequeno demais para o cálculo ou
    quando não há variação nenhuma.
    """
    n = len(matriz)
    if n < 2:
        return None
    k = len(matriz[0])
    if k < 2 or any(len(linha) != k for linha in matriz):
        return None

    valores = [v for linha in matriz for v in linha]
    grande = statistics.fmean(valores)
    media_linha = [statistics.fmean(linha) for linha in matriz]
    media_coluna = [
        statistics.fmean([matriz[i][j] for i in range(n)]) for j in range(k)
    ]

    ss_total = sum((v - grande) ** 2 for v in valores)
    ss_linha = k * sum((m - grande) ** 2 for m in media_linha)
    ss_coluna = n * sum((m - grande) ** 2 for m in media_coluna)
    ss_erro = ss_total - ss_linha - ss_coluna

    ms_linha = ss_linha / (n - 1)
    ms_coluna = ss_coluna / (k - 1)
    ms_erro = ss_erro / ((n - 1) * (k - 1))

    denominador = ms_linha + (k - 1) * ms_erro + k * (ms_coluna - ms_erro) / n
    if denominador == 0:
        return None
    return (ms_linha - ms_erro) / denominador


def ic_bootstrap(
    matriz: list[list[float]], repeticoes: int = BOOTSTRAP
) -> tuple[float, float] | None:
    """Percentis 2,5 e 97,5 do ICC reamostrando redações com reposição."""
    rng = random.Random(SEMENTE)
    n = len(matriz)
    amostras = []
    for _ in range(repeticoes):
        reamostra = [matriz[rng.randrange(n)] for _ in range(n)]
        valor = icc21(reamostra)
        if valor is not None:
            amostras.append(valor)
    if len(amostras) < repeticoes // 2:
        return None
    amostras.sort()
    return amostras[int(0.025 * len(amostras))], amostras[
        int(0.975 * len(amostras)) - 1
    ]


def sem(matriz: list[list[float]], icc: float) -> float:
    """Erro padrão de medida em pontos da rubrica: o desvio observado vezes sqrt(1 - ICC)."""
    valores = [v for linha in matriz for v in linha]
    return statistics.stdev(valores) * ((1 - icc) ** 0.5 if icc < 1 else 0.0)


def notas_por_criterio(
    manifesto: dict,
) -> tuple[dict[str, dict[str, dict[str, float]]], list[str], list[str]]:
    """{criterio: {redacao: {execucao: nota}}}, mais a lista de execuções e de redações vistas."""
    tabela: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    execucoes: set[str] = set()
    redacoes: set[str] = set()
    for job in manifesto["jobs"]:
        if not job.get("result"):
            continue
        redacao = job.get("source_label") or str(job["submission_id"])
        execucao = job.get("run_label") or "sem-rotulo"
        execucoes.add(execucao)
        redacoes.add(redacao)
        for criterio, dados in job["result"]["scores"].items():
            nota = dados.get("nota") if isinstance(dados, dict) else dados
            if nota is not None:
                tabela[criterio][redacao][execucao] = float(nota)
    return tabela, sorted(execucoes), sorted(redacoes)


def matriz_completa(
    por_redacao: dict[str, dict[str, float]], execucoes: list[str]
) -> tuple[list[list[float]], list[str]]:
    """Só redações com nota em todas as execuções; o ICC exige desenho completo."""
    matriz, usadas = [], []
    for redacao in sorted(por_redacao):
        notas = por_redacao[redacao]
        if all(e in notas for e in execucoes):
            matriz.append([notas[e] for e in execucoes])
            usadas.append(redacao)
    return matriz, usadas


def juntar(manifestos: list[dict]) -> dict:
    return {
        "batch_id": ", ".join(str(m["batch_id"])[:8] for m in manifestos),
        "jobs": [job for m in manifestos for job in m["jobs"]],
    }


def relatar(manifesto: dict) -> None:
    tabela, execucoes, redacoes = notas_por_criterio(manifesto)
    if not tabela:
        print("nenhum job com resultado no manifesto.")
        return

    print(f"lote(s) {manifesto['batch_id']}")
    print(f"execucoes: {len(execucoes)} ({', '.join(execucoes)})")
    print(f"redacoes com ao menos um resultado: {len(redacoes)}\n")
    print(
        f"{'criterio':<20} {'n':>3} {'ICC(2,1)':>9} {'IC 95%':>16} {'SEM':>6} {'iguais':>7} {'amplitude':>10}"
    )
    print("-" * 78)

    for criterio in sorted(tabela):
        matriz, usadas = matriz_completa(tabela[criterio], execucoes)
        if len(matriz) < 2:
            print(
                f"{criterio:<20} {len(matriz):>3}  desenho incompleto demais para o calculo"
            )
            continue
        icc = icc21(matriz)
        iguais = sum(1 for linha in matriz if len(set(linha)) == 1) / len(matriz)
        amplitude = statistics.fmean([max(linha) - min(linha) for linha in matriz])
        if icc is None:
            print(
                f"{criterio:<20} {len(matriz):>3}  sem variacao entre redacoes; ICC indefinido"
            )
            continue
        ic = ic_bootstrap(matriz)
        faixa = f"[{ic[0]:.2f}, {ic[1]:.2f}]" if ic else "—"
        print(
            f"{criterio:<20} {len(matriz):>3} {icc:>9.3f} {faixa:>16} {sem(matriz, icc):>6.2f} {iguais:>6.0%} {amplitude:>10.2f}"
        )

    descartadas = len(redacoes) - len(
        matriz_completa(tabela[sorted(tabela)[0]], execucoes)[1]
    )
    print("-" * 78)
    print(
        f"redacoes fora do calculo por falta de nota em alguma execucao: {descartadas}"
    )
    print(
        "\nICC mede repetibilidade, nao acerto. Sem nota humana, a validade de criterio"
    )
    print("permanece nao estabelecida: 'confiavel' nao implica 'correto'.")


def autoteste() -> None:
    """Confere a formula contra o exemplo de Shrout e Fleiss (1979), ICC(2,1) = 0,290."""
    dados = [
        [9, 2, 5, 8],
        [6, 1, 3, 2],
        [8, 4, 6, 8],
        [7, 1, 2, 6],
        [10, 5, 6, 9],
        [6, 2, 4, 7],
    ]
    obtido = icc21([[float(v) for v in linha] for linha in dados])
    assert obtido is not None
    print(f"Shrout & Fleiss (1979): esperado 0.290, obtido {obtido:.3f}")
    assert abs(obtido - 0.290) < 0.001, f"ICC(2,1) fora do esperado: {obtido}"

    identico = [[5.0, 5.0, 5.0], [7.0, 7.0, 7.0], [9.0, 9.0, 9.0]]
    assert abs(icc21(identico) - 1.0) < 1e-9, "execucoes identicas deveriam dar ICC 1"
    assert sem(identico, 1.0) == 0.0, "sem variacao entre execucoes o SEM e zero"

    constante = [[5.0, 5.0], [5.0, 5.0]]
    assert icc21(constante) is None, "sem variacao nenhuma o ICC e indefinido, nao 1"

    print("autoteste ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--autoteste":
        autoteste()
    elif len(sys.argv) >= 2:
        relatar(juntar(carregar(sys.argv[1:])))
    else:
        print(__doc__)
        sys.exit(2)
