# Problemas conhecidos

Bugs abertos, com o mecanismo verificado e o contorno atual. Cada um traz a
correção proposta, ainda não aplicada.

______________________________________________________________________

## 1. Um deploy pode deixar o cluster rodando código antigo, e tudo reporta sucesso

**Estado:** aberto. Contorno abaixo funciona.

### Sintoma

Você muda o código, roda `make deploy`, o Helm responde `STATUS: deployed`, a
API responde `200` — e o comportamento novo não aparece. No caso que originou
este registro, `GET /api/v1/aes/models` continuou listando três provedores
depois de uma feature que adiciona quatro.

### Mecanismo

São três falhas independentes que se somam, e nenhuma delas emite erro.

**A imagem não entra no cluster.** `make build` grava `aes-api:dev` no Docker do
host. O nó do `kind` tem seu próprio containerd — sem `make kind-load`, ele
segue com a imagem anterior. Como `imagePullPolicy` é `IfNotPresent` e a tag não
mudou, o Kubernetes não tenta buscar nada.

**O Helm não reinicia os pods.** `helm upgrade` só provoca rollout se o
manifesto renderizado mudar. Com a mesma tag, os mesmos values e o mesmo
`codeVersion`, o Deployment sai idêntico — então o Helm incrementa a revisão,
responde `deployed`, e não toca nos pods. Verificado: `REVISION: 6`, e o pod
seguia com o `startTime` de oito minutos antes.

**O `codeVersion` vem do git, não da imagem.** O `Makefile` calcula
`CODE_VERSION ?= $(shell git rev-parse --short HEAD)`, e o chart injeta isso
como variável de ambiente que o worker grava em `CorrectionAttempt.code_version`.
Duas consequências:

- Se você commitou entre um deploy e outro, o valor muda, o Deployment muda, e o
  rollout acontece — o bug **não** aparece. É por isso que ele é intermitente.
- Se você não commitou, além de não haver rollout, o `CorrectionAttempt` grava o
  SHA do repositório numa execução que rodou outro código. A rastreabilidade
  exigida pela seção 3.7 do TCC registra algo falso com aparência de precisão.

### Contorno

Rode as três etapas separadas e force o rollout:

```bash
make build
make kind-load
make deploy
kubectl -n aes rollout restart deployment/aes-api-api deployment/aes-api-worker
```

Para confirmar que o pod é novo, compare o `startTime` com o horário atual:

```bash
kubectl -n aes get pod -l app=aes-api-api -o jsonpath='{.items[0].status.startTime}'
```

### Correção proposta

- `deploy` passa a depender de `build` e `kind-load` no `Makefile`.
- O pod template do chart ganha uma anotação derivada do digest da imagem, para
  que uma imagem nova sempre produza um manifesto diferente e force o rollout.
- `codeVersion` passa a vir do digest da imagem em vez do SHA do git, para o
  registro de rastreabilidade não poder divergir do que executou.

______________________________________________________________________

## 2. A API key de bootstrap fica irrecuperável depois de qualquer `make deploy`

**Estado:** aberto. Contorno abaixo funciona, mas envolve `DELETE` em SQL.

### Sintoma

`make creds` imprime `AES_RUBRIC_ID` e `AES_PROMPT_TEMPLATE_ID`, mas não a
chave. Qualquer requisição responde `{"detail":"Invalid API key"}`, e não há
como recuperar o valor.

### Mecanismo

O seed emite a chave uma única vez e a imprime no stdout do Job; `make creds` lê
dos logs desse Job. O hash armazenado é scrypt com salt por linha, irrecuperável
por construção — o valor existe apenas naquela saída.

O Job roda como hook `post-install,post-upgrade`, então **todo `make deploy` o
recria**. O Job novo encontra a chave existente, não reemite (idempotência
deliberada, coberta por teste), e seu log já nasce sem a linha da chave. O log
anterior morre com o Job antigo.

Ou seja: a chave é legível apenas entre a primeira emissão e o deploy seguinte.
Depois disso, existe no banco e é inalcançável.

### Contorno

Apagar a linha para o seed reemitir:

```bash
export KUBECONFIG=~/.kube/kind-aes-local.yaml
PGPW=$(kubectl -n aes get secret aes-api-env -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)
kubectl -n aes exec postgres-0 -- env PGPASSWORD="$PGPW" psql -U aes_app -d postgres -c "DELETE FROM api_keys WHERE name = 'bootstrap';"
make deploy
make creds
```

Guarde o valor: ele volta a ser irrecuperável no próximo deploy.

### Correção proposta

- Um alvo `make reissue-key` que faça delete, redeploy e imprima a chave nova.
- Ou, melhor, o seed grava a chave num Secret do Kubernetes em vez de imprimir
  no log. Foi descartado no desenho original porque exigiria `kubectl` na imagem
  da aplicação mais ServiceAccount, Role e RoleBinding; revisitar essa decisão
  agora que o atrito real é conhecido.

______________________________________________________________________

## 3. Divergência entre `helm upgrade` bem-sucedido e o estado real

**Estado:** aberto, subconjunto do item 1, registrado à parte porque afeta a
leitura de qualquer diagnóstico.

Quatro camadas podem reportar sucesso simultaneamente com o cluster rodando
código antigo: o `docker build` conclui, o `kind load` carrega, o `helm upgrade`
responde `deployed`, e a API responde `200`. Nenhuma mente — cada uma está
correta no seu escopo. O erro mora entre elas, e nenhum comando isolado o
revela.

Ao diagnosticar qualquer comportamento inesperado no cluster, verifique primeiro
se o pod é novo, antes de investigar o código:

```bash
kubectl -n aes get pod -l app=aes-api-api -o jsonpath='{.items[0].status.startTime}'
kubectl -n aes get pod -l app=aes-api-api -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
```

Um detalhe que custou tempo: o estágio `prod` do `backend/Dockerfile` define
`WORKDIR /app/src`. Ao inspecionar arquivos dentro do container, o caminho do
módulo é `modules/aes/...`, não `src/modules/aes/...`.

______________________________________________________________________

## Itens menores, sem contorno necessário

- `TASKIQ_ENABLED` existe em `settings.py` e não é lido em lugar nenhum. Config
  morta; decidir entre honrar ou remover.
- Os handlers `except Exception: raise HTTPException(500, ...)` nas rotas engolem
  o traceback. Já existe `CatchAllErrorMiddleware` fazendo log estruturado, então
  a correção é remover os handlers de rota — refactor que toca toda rota.
- A suíte fica instável sob carga concorrente do Docker: os testes que usam
  testcontainers podem falhar por contenção do daemon. Não é regressão; roda
  verde isoladamente.
- Os testes da CLI cobrem apenas o modo `local` do gerador de compose; `prod` e
  `nginx` não têm cobertura.
