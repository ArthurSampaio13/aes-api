#!/usr/bin/env bash
set -euo pipefail

# Identidade do conteudo da imagem: os diff_ids das camadas nao carregam
# timestamp, entao dois builds do mesmo codigo dao o mesmo valor e qualquer
# mudanca de fonte muda o valor. O digest do indice OCI nao serve: muda a cada
# build por causa da atestacao de proveniencia.
docker image inspect "${IMAGE:-aes-api}:${TAG:-dev}" --format '{{json .RootFS.Layers}}' | sha256sum | cut -c1-12
