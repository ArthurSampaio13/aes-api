#!/usr/bin/env bash
set -euo pipefail

# O seed so imprime a chave na primeira emissao, e o Job e recriado a cada
# deploy levando o log junto. Guardamos o valor num Secret do cluster, que
# sobrevive ao helm upgrade, para ele nao ficar irrecuperavel.
#
#   stash  captura do log do Job, se estiver la, e grava no Secret
#   get    imprime a chave: Secret primeiro, log como fallback

NS="${NS:-aes}"
SECRET="${SECRET:-aes-api-bootstrap-key}"
FIELD=AES_BOOTSTRAP_API_KEY

from_log() {
  kubectl -n "$NS" logs job/aes-api-seed 2>/dev/null | grep "^$FIELD=" | cut -d= -f2- || true
}

from_secret() {
  kubectl -n "$NS" get secret "$SECRET" -o jsonpath="{.data.$FIELD}" 2>/dev/null | base64 -d || true
}

case "${1:-get}" in
get)
  KEY="$(from_secret)"
  [ -n "$KEY" ] || KEY="$(from_log)"
  printf '%s' "$KEY"
  ;;
stash)
  KEY="$(from_log)"
  [ -n "$KEY" ] || exit 0
  kubectl -n "$NS" create secret generic "$SECRET" \
    --from-literal="$FIELD=$KEY" --dry-run=client -o yaml |
    kubectl -n "$NS" apply -f - >/dev/null
  ;;
*)
  echo "uso: $0 [get|stash]" >&2
  exit 2
  ;;
esac
