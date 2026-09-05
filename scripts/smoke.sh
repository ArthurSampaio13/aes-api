#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
NS="${NS:-aes}"

log() { printf '\033[0;34m==>\033[0m %s\n' "$1"; }
die() { printf '\033[0;31mFALHOU:\033[0m %s\n' "$1" >&2; exit 1; }

SEED_LOG="$(kubectl -n "$NS" logs job/aes-api-seed 2>/dev/null || true)"
API_KEY="${API_KEY:-$(printf '%s' "$SEED_LOG" | grep '^AES_BOOTSTRAP_API_KEY=' | cut -d= -f2-)}"
RUBRIC_ID="$(printf '%s' "$SEED_LOG" | grep '^AES_RUBRIC_ID=' | cut -d= -f2-)"
PROMPT_TEMPLATE_ID="$(printf '%s' "$SEED_LOG" | grep '^AES_PROMPT_TEMPLATE_ID=' | cut -d= -f2-)"
[ -n "$API_KEY" ] || die "API key de bootstrap não encontrada nos logs do seed (ele não reemite a chave); passe API_KEY=... no ambiente"
[ -n "$RUBRIC_ID" ] || die "rubric id não encontrado nos logs do seed"
[ -n "$PROMPT_TEMPLATE_ID" ] || die "prompt template id não encontrado nos logs do seed"
AUTH=(-H "X-API-Key: $API_KEY" -H "Content-Type: application/json")

log "health"
[ "$(curl -sf "$API/health" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')" = "healthy" ] \
  || die "health não retornou healthy"

log "models"
curl -sf "${AUTH[@]}" "$API/api/v1/aes/models" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); assert any(m["provider"]=="mock" for m in d), d' \
  || die "provedor mock ausente em /aes/models"

log "essay prompt"
PROMPT_UUID="$(curl -sf "${AUTH[@]}" -X POST "$API/api/v1/aes/essay-prompts" -d "{
  \"titulo\": \"O rio da minha cidade\",
  \"enunciado\": \"Escreva um artigo de opinião sobre a importância de cuidar do rio da sua cidade.\",
  \"ano_escolar\": \"9\",
  \"genero_textual\": \"artigo de opinião\",
  \"support_texts\": [],
  \"rubric_id\": $RUBRIC_ID,
  \"prompt_template_id\": $PROMPT_TEMPLATE_ID
}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["uuid"])')"
[ -n "$PROMPT_UUID" ] || die "essay prompt não foi criado"

log "submit batch"
JOB_ID="$(curl -sf "${AUTH[@]}" -X POST "$API/api/v1/aes/jobs" -d "{
  \"essay_prompt_uuid\": \"$PROMPT_UUID\",
  \"texts\": [\"O rio da minha cidade esta muito sujo. As pessoas jogam lixo nele todo dia. Precisamos cuidar melhor dele para o futuro.\"],
  \"provider\": \"mock\",
  \"model\": \"mock-v1\"
}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_ids"][0])')"
[ -n "$JOB_ID" ] || die "job não foi criado"

log "aguardando o worker (job $JOB_ID)"
for i in $(seq 1 60); do
  STATUS="$(curl -sf "${AUTH[@]}" "$API/api/v1/aes/jobs/$JOB_ID" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [ "$STATUS" = "done" ] && break
  [ "$STATUS" = "failed" ] && die "job terminou como failed"
  [ "$i" -eq 60 ] && die "job não concluiu em 5 minutos (último status: $STATUS)"
  sleep 5
done

log "resultados"
curl -sf "${AUTH[@]}" "$API/api/v1/aes/jobs/$JOB_ID/results" | python3 -c '
import json, sys
r = json.load(sys.stdin)
assert r["requires_teacher_review"] is True, "requires_teacher_review deveria ser True"
assert r["feedback"], "feedback vazio"
assert r["sugestao_acionavel"], "sugestao_acionavel vazia"
expected = {"adequacao_tema","estrutura_textual","coesao_coerencia","adequacao_ling","vocabulario"}
actual = set(r["scores"])
assert actual == expected, f"critérios inesperados: {actual}"
print("resultado completo, com os cinco critérios e sugestão acionável")
' || die "resultado inválido"

printf '\033[0;32mSMOKE OK\033[0m\n'
