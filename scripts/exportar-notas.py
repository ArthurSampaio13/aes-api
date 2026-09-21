#!/usr/bin/env python3
"""Extrai dos manifestos a tabela de resultados, sem nenhum texto de aluno.

    scripts/exportar-notas.py <destino/> .local/manifests/<batch>.json [outro.json ...]
    scripts/exportar-notas.py --autoteste

Gera três CSV:

- `notas.csv`        — uma linha por redação × execução × critério: a nota.
- `tentativas.csv`   — uma linha por tentativa: condições, tokens, custo, latência, guards.
- `transcricoes.csv` — uma linha por redação: metadados do OCR.

O que **não** sai: `feedback`, `sugestao_acionavel`, `justificativa`, `raw_text` e
qualquer referência a objeto no storage. Esses campos citam a redação do aluno; a
tabela existe justamente para os números poderem circular sem eles.

A redação aparece só pelo rótulo (`9A-01`), que é numerado e não deriva do nome do
arquivo. O mapa rótulo → arquivo fica fora daqui, e é o único artefato que
reidentifica alguém.
"""

import csv
import json
import pathlib
import sys

NOTAS = ["rotulo", "turma", "execucao", "criterio", "nota"]
TENTATIVAS = [
    "rotulo",
    "turma",
    "execucao",
    "job_id",
    "attempt_number",
    "outcome",
    "status_job",
    "provider",
    "model",
    "served_provider",
    "prompt_version",
    "rubric_version",
    "code_version",
    "temperature",
    "seed",
    "cache_ttl",
    "tokens_in",
    "tokens_out",
    "cache_read_tokens",
    "cache_write_tokens",
    "cost_usd",
    "cost_source",
    "latency_ms",
    "model_retries",
    "guard_retries",
    "guards_disparados",
]
TRANSCRICOES = [
    "rotulo",
    "turma",
    "input_type",
    "palavras",
    "transcricao_completa",
    "trechos_ilegiveis",
    "model",
    "served_provider",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "cost_source",
    "latency_ms",
    "model_retries",
]


def turma(rotulo: str) -> str:
    return rotulo.split("-")[0] if "-" in rotulo else ""


def linhas(manifestos: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    notas, tentativas, transcricoes, vistas = [], [], [], set()
    for manifesto in manifestos:
        for job in manifesto["jobs"]:
            rotulo = job.get("source_label") or str(job["submission_id"])
            execucao = job.get("run_label") or ""
            t = turma(rotulo)

            if job.get("result"):
                for criterio, dados in sorted(job["result"]["scores"].items()):
                    nota = dados.get("nota") if isinstance(dados, dict) else dados
                    notas.append(
                        {
                            "rotulo": rotulo,
                            "turma": t,
                            "execucao": execucao,
                            "criterio": criterio,
                            "nota": nota,
                        }
                    )

            for a in job["attempts"]:
                params = a.get("inference_params") or {}
                eventos = a.get("guardrail_events") or []
                tentativas.append(
                    {
                        "rotulo": rotulo,
                        "turma": t,
                        "execucao": execucao,
                        "job_id": job["job_id"],
                        "attempt_number": a["attempt_number"],
                        "outcome": a["outcome"],
                        "status_job": job["status"],
                        "provider": a["provider"],
                        "model": a["model"],
                        "served_provider": a["served_provider"],
                        "prompt_version": a["prompt_version"],
                        "rubric_version": a["rubric_version"],
                        "code_version": a["code_version"],
                        "temperature": params.get("temperature"),
                        "seed": params.get("seed"),
                        "cache_ttl": params.get("openrouter_cache_instructions"),
                        "tokens_in": a["tokens_in"],
                        "tokens_out": a["tokens_out"],
                        "cache_read_tokens": a["cache_read_tokens"],
                        "cache_write_tokens": a["cache_write_tokens"],
                        "cost_usd": a["cost_usd"],
                        "cost_source": a["cost_source"],
                        "latency_ms": a["latency_ms"],
                        "model_retries": a["model_retries"],
                        "guard_retries": sum(
                            1 for e in eventos if e.get("veredito") == "retry"
                        ),
                        "guards_disparados": "|".join(
                            sorted(
                                {
                                    e.get("guard", "")
                                    for e in eventos
                                    if e.get("veredito") == "retry"
                                }
                            )
                        ),
                    }
                )

            if rotulo not in vistas:
                vistas.add(rotulo)
                tr = job.get("transcription") or {}
                transcricoes.append(
                    {
                        "rotulo": rotulo,
                        "turma": t,
                        "input_type": job["input_type"],
                        "palavras": tr.get("palavras"),
                        "transcricao_completa": tr.get("transcricao_completa"),
                        "trechos_ilegiveis": tr.get("trechos_ilegiveis"),
                        "model": tr.get("model"),
                        "served_provider": tr.get("served_provider"),
                        "tokens_in": tr.get("tokens_in"),
                        "tokens_out": tr.get("tokens_out"),
                        "cost_usd": tr.get("cost_usd"),
                        "cost_source": tr.get("cost_source"),
                        "latency_ms": tr.get("latency_ms"),
                        "model_retries": tr.get("model_retries"),
                    }
                )
    return notas, tentativas, transcricoes


def gravar(
    destino: pathlib.Path, nome: str, campos: list[str], dados: list[dict]
) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome
    with caminho.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(
            sorted(dados, key=lambda d: tuple(str(d.get(c, "")) for c in campos[:4]))
        )
    print(f"{caminho}: {len(dados)} linhas")


def exportar(destino: pathlib.Path, manifestos: list[dict]) -> None:
    notas, tentativas, transcricoes = linhas(manifestos)
    gravar(destino, "notas.csv", NOTAS, notas)
    gravar(destino, "tentativas.csv", TENTATIVAS, tentativas)
    gravar(destino, "transcricoes.csv", TRANSCRICOES, transcricoes)


def autoteste() -> None:
    """Garante que nenhum campo de texto livre atravessa a exportação."""
    manifesto = {
        "batch_id": "0" * 8,
        "jobs": [
            {
                "job_id": "j1",
                "submission_id": "s1",
                "source_label": "9A-01",
                "run_label": "run-1",
                "status": "done",
                "input_type": "image",
                "transcription": {
                    "palavras": 80,
                    "model": "m",
                    "raw_exchange_ref": "transcriptions/s1/x.json",
                },
                "attempts": [
                    {
                        "attempt_number": 1,
                        "outcome": "success",
                        "provider": "openrouter",
                        "model": "m",
                        "served_provider": "B",
                        "prompt_version": 1,
                        "rubric_version": 1,
                        "code_version": "c",
                        "inference_params": {"temperature": 0.0, "seed": 42},
                        "tokens_in": 10,
                        "tokens_out": 20,
                        "cache_read_tokens": None,
                        "cache_write_tokens": None,
                        "cost_usd": "0.001",
                        "cost_source": "charged",
                        "latency_ms": 100,
                        "model_retries": 0,
                        "guardrail_events": [
                            {
                                "guard": "citacoes",
                                "veredito": "retry",
                                "motivo": "citou 'O rio da minha cidade'",
                            }
                        ],
                        "raw_request_ref": "correction-attempts/j1/request.json",
                        "raw_response_ref": "correction-attempts/j1/response.json",
                    }
                ],
                "result": {
                    "scores": {
                        "adequacao_tema": {
                            "nota": 7,
                            "justificativa": "O aluno escreveu 'meu bairro tem cachorros'",
                        }
                    },
                    "feedback": "Seu texto sobre os animais do bairro esta bom",
                    "sugestao_acionavel": "Releia o trecho 'os cachorros ficam na rua'",
                    "requires_teacher_review": True,
                },
            }
        ],
    }
    notas, tentativas, transcricoes = linhas([manifesto])
    assert notas == [
        {
            "rotulo": "9A-01",
            "turma": "9A",
            "execucao": "run-1",
            "criterio": "adequacao_tema",
            "nota": 7,
        }
    ]
    assert (
        tentativas[0]["guard_retries"] == 1
        and tentativas[0]["guards_disparados"] == "citacoes"
    )

    despejo = json.dumps([notas, tentativas, transcricoes], default=str)
    for vazado in (
        "cachorros",
        "bairro",
        "rio da minha cidade",
        "justificativa",
        "feedback",
        "sugestao",
        "raw_request_ref",
        "raw_response_ref",
        "raw_exchange_ref",
        "motivo",
    ):
        assert (
            vazado not in despejo
        ), f"texto de aluno ou ponteiro vazou na exportacao: {vazado}"

    assert turma("9A-01") == "9A" and turma("solto") == ""
    print("autoteste ok: nenhum texto livre atravessa a exportacao")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--autoteste":
        autoteste()
    elif len(sys.argv) >= 3:
        exportar(
            pathlib.Path(sys.argv[1]),
            [json.load(open(c, encoding="utf-8")) for c in sys.argv[2:]],
        )
    else:
        print(__doc__)
        sys.exit(2)
