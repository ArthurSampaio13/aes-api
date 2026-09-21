#!/usr/bin/env bash
# Repete a correcao de um lote k vezes e exporta o manifesto ao final.
#
#   scripts/experimento.sh <batch_id> [k]
#
# A primeira execucao e a do envio (scripts/enviar-redacoes.sh, run-1). Esta aqui
# faz as execucoes 2..k sobre as mesmas submissoes: a transcricao ja esta gravada,
# entao o OCR nao roda de novo e o que varia entre execucoes e so o corretor.
set -euo pipefail

API="${API:-http://localhost:8000}"
PROVIDER="${PROVIDER:-openrouter}"
MODEL="${MODEL:-}"
OUT="${OUT:-.local/manifests}"
INTERVALO="${INTERVALO:-10}"

die() { printf '\033[0;31merro:\033[0m %s\n' "$1" >&2; exit 1; }

[ $# -ge 1 ] || die "uso: $0 <batch_id> [k]"
BATCH="$1"
K="${2:-5}"

API_KEY="${API_KEY:-$("$(dirname "$0")/bootstrap-key.sh" get)}"
[ -n "$API_KEY" ] || die "sem API key; rode make reissue-key"

manifesto() {
  curl -sf -H "X-API-Key: $API_KEY" "$API/api/v1/aes/batches/$BATCH/manifest"
}

pendentes() {
  manifesto | python3 -c 'import json,sys; print(sum(1 for j in json.load(sys.stdin)["jobs"] if j["status"] not in ("done", "failed")))'
}

aguardar() {
  while :; do
    n="$(pendentes)"
    if [ "$n" -eq 0 ]; then
      printf '\r  lote completo.        \n'
      return
    fi
    printf '\r  %s job(s) pendente(s)...' "$n"
    sleep "$INTERVALO"
  done
}

echo "aguardando a execucao ja em andamento..."
aguardar

for i in $(seq 2 "$K"); do
  echo "execucao run-$i de $K"
  corpo="$(python3 -c 'import json,sys; print(json.dumps({"run_label": sys.argv[1], "provider": sys.argv[2], **({"model": sys.argv[3]} if sys.argv[3] else {})}))' "run-$i" "$PROVIDER" "$MODEL")"
  curl -sf -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
    -X POST "$API/api/v1/aes/batches/$BATCH/corrections" -d "$corpo" >/dev/null ||
    die "a API recusou a execucao run-$i"
  aguardar
done

mkdir -p "$OUT"
manifesto >"$OUT/$BATCH.json"
python3 - "$OUT/$BATCH.json" <<'PY'
import collections, json, sys

jobs = json.load(open(sys.argv[1]))["jobs"]
por_execucao = collections.Counter(j["run_label"] for j in jobs)
por_status = collections.Counter(j["status"] for j in jobs)
redacoes = {j["source_label"] for j in jobs}
print(f"\nmanifesto: {sys.argv[1]}")
print(f"  redacoes: {len(redacoes)}")
print(f"  execucoes: {dict(sorted(por_execucao.items(), key=lambda kv: str(kv[0])))}")
print(f"  status: {dict(por_status)}")
PY
