#!/usr/bin/env bash
# Le {"kubeconfig": "..."} do stdin e devolve {"jwks": "<json do cluster>"}.
# O kube-apiserver expoe as chaves publicas de assinatura em /openid/v1/jwks;
# e esse documento que a AWS busca no bucket para validar o token do pod.
set -euo pipefail

KUBECONFIG_PATH="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["kubeconfig"])')"
export KUBECONFIG="$KUBECONFIG_PATH"

JWKS="$(kubectl get --raw /openid/v1/jwks)"
python3 -c 'import json,sys; print(json.dumps({"jwks": sys.argv[1]}))' "$JWKS"
