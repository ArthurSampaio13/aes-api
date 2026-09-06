#!/usr/bin/env bash
# Envia um lote de redacoes digitalizadas para correcao.
#
#   scripts/enviar-redacoes.sh <essay_prompt_uuid> arquivo... [-- provider model]
#
# O Swagger so adiciona um arquivo por vez; a rota aceita ate 50 por requisicao.
set -euo pipefail

API="${API:-http://localhost:8000}"
NS="${NS:-aes}"
PROVIDER="${PROVIDER:-mock}"
MODEL="${MODEL:-mock-v1}"

die() { printf '\033[0;31merro:\033[0m %s\n' "$1" >&2; exit 1; }

[ $# -ge 2 ] || die "uso: $0 <essay_prompt_uuid> arquivo..."
PROMPT_UUID="$1"; shift

API_KEY="${API_KEY:-$("$(dirname "$0")/bootstrap-key.sh" get)}"
[ -n "$API_KEY" ] || die "sem API key; rode make reissue-key"

# Aceita caminho do Windows (C:\...) sob WSL e expande curinga que veio entre
# aspas — o shell nao expande "*.pdf" citado, e o script receberia o literal.
# IFS de nova linha para nome com espaco nao virar dois argumentos.
expandir() {
  local raw="$1" matches=()
  case "$raw" in
    [A-Za-z]:[\\/]*) raw="$(wslpath -u "$raw" 2>/dev/null || printf '%s' "$raw")" ;;
  esac
  case "$raw" in
    *[*?]*)
      local IFS=$'\n'
      shopt -s nullglob
      # shellcheck disable=SC2206  # a expansao do curinga aqui e o objetivo
      matches=($raw)
      shopt -u nullglob
      [ ${#matches[@]} -gt 0 ] || die "nenhum arquivo casa com: $raw"
      printf '%s\n' "${matches[@]}"
      ;;
    *) printf '%s\n' "$raw" ;;
  esac
}

arquivos=()
for pattern in "$@"; do
  while IFS= read -r found; do
    arquivos+=("$found")
  done < <(expandir "$pattern")
done

args=(-F "essay_prompt_uuid=$PROMPT_UUID" -F "provider=$PROVIDER" -F "model=$MODEL")
for f in "${arquivos[@]}"; do
  [ -f "$f" ] || die "arquivo nao encontrado: $f"
  case "${f,,}" in
    *.jpg | *.jpeg) t=image/jpeg ;;
    *.png) t=image/png ;;
    *.pdf) t=application/pdf ;;
    *) die "formato nao aceito: $f (use jpg, png ou pdf de 1 pagina)" ;;
  esac
  args+=(-F "images=@${f};type=${t}")
done

echo "enviando ${#arquivos[@]} arquivo(s) com provider=$PROVIDER..."
RESPONSE="$(curl -sf -H "X-API-Key: $API_KEY" -X POST "$API/api/v1/aes/jobs/images" "${args[@]}")" ||
  die "a API recusou o lote"

python3 - "$RESPONSE" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
print(f"batch {d['batch_id']}")
for job in d["job_ids"]:
    print(f"  job {job}")
PY

cat <<'TXT'

Acompanhe com:
  curl -s -H "X-API-Key: $API_KEY" $API/api/v1/aes/jobs/<job_id>
  curl -s -H "X-API-Key: $API_KEY" $API/api/v1/aes/jobs/<job_id>/results

Transcricoes do OCR (o RLS esconde as linhas do usuario da aplicacao, entao use o superusuario):
  PGPW=$(kubectl -n aes get secret postgres-credentials -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)
  kubectl -n aes exec postgres-0 -- env PGPASSWORD="$PGPW" psql -U postgres -d postgres \
    -c "SELECT uuid, raw_text FROM submissions ORDER BY created_at DESC LIMIT 20;"
TXT
