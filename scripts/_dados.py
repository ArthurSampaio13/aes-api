"""Carrega notas para análise a partir de manifesto de lote ou de `notas.csv`.

As duas fontes produzem a mesma estrutura, para que os números possam ser recalculados a partir da tabela derivada — que
não contém texto de aluno — sem depender dos manifestos, que contêm.
"""

import csv
import json
import pathlib
from collections import defaultdict


def _do_csv(caminho: pathlib.Path) -> dict:
    """Reconstrói jobs mínimos a partir de notas.csv: rótulo, execução e as notas."""
    por_job: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    with caminho.open(encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            if linha.get("nota") in (None, ""):
                continue
            por_job[(linha["rotulo"], linha["execucao"])][linha["criterio"]] = float(
                linha["nota"]
            )
    jobs = [
        {
            "job_id": f"{rotulo}:{execucao}",
            "submission_id": rotulo,
            "source_label": rotulo,
            "run_label": execucao or None,
            "status": "done",
            "input_type": "",
            "transcription": None,
            "attempts": [],
            "result": {"scores": {c: {"nota": n} for c, n in sorted(notas.items())}},
        }
        for (rotulo, execucao), notas in sorted(por_job.items())
    ]
    return {"batch_id": caminho.stem, "jobs": jobs}


def carregar(caminhos: list[str]) -> list[dict]:
    fontes = []
    for bruto in caminhos:
        caminho = pathlib.Path(bruto)
        if caminho.suffix == ".csv":
            fontes.append(_do_csv(caminho))
        else:
            fontes.append(json.loads(caminho.read_text(encoding="utf-8")))
    return fontes
