#!/usr/bin/env python3
"""Como as notas se distribuem, e se os cinco critérios produzem cinco sinais distintos.

    scripts/analise-distribuicao.py <manifesto.json|notas.csv> [outro ...]
    scripts/analise-distribuicao.py --autoteste

Cada redação entra pela média das suas k execuções, o que reduz o ruído de execução
antes de olhar a distribuição. A turma sai do prefixo do rótulo (9A-01 -> 9A).

A matriz de correlação responde a pergunta de estrutura interna: se os critérios se
movem quase juntos, a rubrica produz menos dimensões do que os cinco que declara. Lai,
Wolfe e Vickers documentam que escores analíticos humanos de redação raramente
distinguem mais de duas dimensões, então correlação alta aqui replica um padrão
conhecido em vez de denunciar um defeito do sistema.

Spearman, não Pearson: nota de rubrica é ordinal. Correlação alta não prova que os
construtos sejam indistinguíveis nos alunos, só que estas saídas não os distinguem.
"""

import pathlib
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from _dados import carregar  # noqa: E402

CRITERIOS = [
    "adequacao_tema",
    "estrutura_textual",
    "coesao_coerencia",
    "adequacao_ling",
    "vocabulario",
]


def postos(valores: list[float]) -> list[float]:
    """Postos com média nos empates, como o Spearman exige."""
    ordenado = sorted(range(len(valores)), key=lambda i: valores[i])
    resultado = [0.0] * len(valores)
    i = 0
    while i < len(ordenado):
        j = i
        while (
            j + 1 < len(ordenado) and valores[ordenado[j + 1]] == valores[ordenado[i]]
        ):
            j += 1
        media_posto = (i + j) / 2 + 1
        for k in range(i, j + 1):
            resultado[ordenado[k]] = media_posto
        i = j + 1
    return resultado


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 2:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return None if den == 0 else num / den


def spearman(x: list[float], y: list[float]) -> float | None:
    return pearson(postos(x), postos(y))


def media_por_redacao(manifestos: list[dict]) -> dict[str, dict[str, float]]:
    """{redacao: {criterio: media das execucoes}}."""
    bruto: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for manifesto in manifestos:
        for job in manifesto["jobs"]:
            if not job.get("result"):
                continue
            redacao = job.get("source_label") or str(job["submission_id"])
            for criterio, dados in job["result"]["scores"].items():
                nota = dados.get("nota") if isinstance(dados, dict) else dados
                if nota is not None:
                    bruto[redacao][criterio].append(float(nota))
    return {
        r: {c: statistics.fmean(v) for c, v in criterios.items()}
        for r, criterios in bruto.items()
    }


def turma(rotulo: str) -> str:
    return rotulo.split("-")[0] if "-" in rotulo else "sem-turma"


def descrever(valores: list[float]) -> str:
    q = statistics.quantiles(valores, n=4) if len(valores) >= 4 else [float("nan")] * 3
    return (
        f"{statistics.fmean(valores):>6.2f} {statistics.stdev(valores) if len(valores) > 1 else 0:>6.2f} "
        f"{min(valores):>5.1f} {q[0]:>5.1f} {q[1]:>5.1f} {q[2]:>5.1f} {max(valores):>5.1f}"
    )


def relatar(manifestos: list[dict]) -> None:
    notas = media_por_redacao(manifestos)
    if not notas:
        print("nenhum job com resultado.")
        return
    criterios = [c for c in CRITERIOS if any(c in v for v in notas.values())]
    turmas = sorted({turma(r) for r in notas})

    print(f"redacoes: {len(notas)} | turmas: {', '.join(turmas)}")
    print("cada redacao entra pela media das suas execucoes\n")

    print(
        f"{'criterio':<20} {'media':>6} {'dp':>6} {'min':>5} {'q1':>5} {'med':>5} {'q3':>5} {'max':>5}"
    )
    print("-" * 66)
    for criterio in criterios:
        valores = [v[criterio] for v in notas.values() if criterio in v]
        print(f"{criterio:<20} {descrever(valores)}")
    geral = [
        statistics.fmean([v[c] for c in criterios if c in v]) for v in notas.values()
    ]
    print(f"{'media dos criterios':<20} {descrever(geral)}")

    print(
        f"\n{'turma':<8} {'n':>4} "
        + " ".join(f"{c[:12]:>12}" for c in criterios)
        + f" {'geral':>8}"
    )
    print("-" * (14 + 13 * len(criterios) + 9))
    for t in turmas:
        desta = [v for r, v in notas.items() if turma(r) == t]
        medias = " ".join(
            f"{statistics.fmean([v[c] for v in desta if c in v]):>12.2f}"
            for c in criterios
        )
        todos = [statistics.fmean([v[c] for c in criterios if c in v]) for v in desta]
        print(f"{t:<8} {len(desta):>4} {medias} {statistics.fmean(todos):>8.2f}")

    print("\ncorrelacao de Spearman entre criterios (media das execucoes por redacao)")
    print(f"{'':<20}" + " ".join(f"{c[:12]:>12}" for c in criterios))
    comuns = [r for r, v in notas.items() if all(c in v for c in criterios)]
    for a in criterios:
        linha = []
        for b in criterios:
            rho = spearman([notas[r][a] for r in comuns], [notas[r][b] for r in comuns])
            linha.append(f"{rho:>12.2f}" if rho is not None else f"{'—':>12}")
        print(f"{a:<20}" + " ".join(linha))

    fora = [(a, b) for i, a in enumerate(criterios) for b in criterios[i + 1 :]]
    pares = [
        (a, b, spearman([notas[r][a] for r in comuns], [notas[r][b] for r in comuns]))
        for a, b in fora
    ]
    validos = [p for p in pares if p[2] is not None]
    if validos:
        maior = max(validos, key=lambda p: p[2])
        menor = min(validos, key=lambda p: p[2])
        print(f"\npar mais redundante: {maior[0]} x {maior[1]} (rho {maior[2]:.2f})")
        print(f"par mais distinto:   {menor[0]} x {menor[1]} (rho {menor[2]:.2f})")
        print(
            f"correlacao media entre pares: {statistics.fmean(p[2] for p in validos):.2f}"
        )

    print(
        "\nDistribuicao e correlacao descrevem as saidas deste sistema, nao os alunos."
    )
    print("Sem nota humana, nada aqui diz se o nivel absoluto das notas esta certo.")


def autoteste() -> None:
    """Confere o Spearman contra o exemplo de QI x horas de TV da Wikipedia, rho = -0,1758."""
    qi = [106.0, 86, 100, 101, 99, 103, 97, 113, 112, 110]
    tv = [7.0, 0, 27, 50, 28, 29, 20, 12, 6, 17]
    obtido = spearman(qi, tv)
    assert obtido is not None
    print(f"Wikipedia QI x TV: esperado -0.1758, obtido {obtido:.4f}")
    assert (
        abs(obtido - (-0.175757575757576)) < 1e-6
    ), f"Spearman fora do esperado: {obtido}"

    assert (
        abs(spearman([1.0, 2, 3, 4], [10.0, 20, 30, 40]) - 1.0) < 1e-12
    ), "monotonica crescente e 1"
    assert (
        abs(spearman([1.0, 2, 3, 4], [40.0, 30, 20, 10]) + 1.0) < 1e-12
    ), "monotonica decrescente e -1"
    assert (
        spearman([1.0, 1, 1], [1.0, 2, 3]) is None
    ), "sem variacao a correlacao e indefinida"
    assert postos([10.0, 20, 20, 30]) == [
        1.0,
        2.5,
        2.5,
        4.0,
    ], "empate recebe a media dos postos"

    print("autoteste ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--autoteste":
        autoteste()
    elif len(sys.argv) >= 2:
        relatar(carregar(sys.argv[1:]))
    else:
        print(__doc__)
        sys.exit(2)
