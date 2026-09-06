# Problemas conhecidos

Os dois bugs de deploy registrados aqui foram corrigidos e estão descritos
abaixo com o mecanismo e a correção aplicada. O que segue aberto está na
seção final.

______________________________________________________________________

## 1. Um deploy podia deixar o cluster rodando código antigo (corrigido)

**Estado:** corrigido. `make deploy` reconstrói, carrega e força o rollout.

### Sintoma

Você mudava o código, rodava `make deploy`, o Helm respondia `STATUS: deployed`,
a API respondia `200` — e o comportamento novo não aparecia. No caso que
originou este registro, `GET /api/v1/aes/models` continuou listando três
provedores depois de uma feature que adiciona quatro.

### Mecanismo

Eram três falhas independentes que se somavam, e nenhuma delas emitia erro.

**A imagem não entrava no cluster.** `make build` grava `aes-api:dev` no Docker
do host. O nó do `kind` tem seu próprio containerd — sem `make kind-load`, ele
seguia com a imagem anterior. Como `imagePullPolicy` é `IfNotPresent` e a tag
não muda, o Kubernetes não tentava buscar nada.

**O Helm não reiniciava os pods.** `helm upgrade` só provoca rollout se o
manifesto renderizado mudar. Com a mesma tag, os mesmos values e o mesmo
`codeVersion`, o Deployment saía idêntico — então o Helm incrementava a
revisão, respondia `deployed`, e não tocava nos pods.

**O `codeVersion` vinha do git, não da imagem.** O `Makefile` calculava
`CODE_VERSION ?= $(shell git rev-parse --short HEAD)`, e o chart injeta isso
como variável de ambiente que o worker grava em `CorrectionAttempt.code_version`.
Se você não tivesse commitado, além de não haver rollout, o `CorrectionAttempt`
gravava o SHA do repositório numa execução que rodou outro código — a
rastreabilidade exigida pela seção 3.7 do TCC registrava algo falso com
aparência de precisão. Se você tivesse commitado entre um deploy e outro, o
valor mudava, o Deployment mudava e o rollout acontecia: por isso o bug era
intermitente.

### Correção aplicada

- `deploy` passou a depender de `build` e `kind-load`, então `make deploy`
  sozinho cobre o ciclo. `up` virou `infra deploy creds`.
- `codeVersion` passou a sair do conteúdo da imagem
  (`scripts/code-version.sh`). Como esse valor já é injetado como env nos dois
  Deployments, uma imagem nova muda o manifesto e força o rollout — não foi
  preciso adicionar anotação nenhuma ao pod template.
- `deploy` aborta se o `codeVersion` sair vazio, em vez de registrar
  rastreabilidade em branco.
- `deploy` espera o `rollout status` das duas Deployments. O `helm --wait`
  sozinho não basta: ele retorna quando o pod novo está pronto, mas o antigo
  ainda pode estar vivo e recebendo tráfego do Service por alguns segundos.
- `make smoke` compara o `CODE_VERSION` dos pods vivos com o da imagem local e
  falha se divergirem (pods em terminação são ignorados, senão a checagem
  acusaria falso positivo no meio de um rollout).

### Por que o identificador são as camadas, e não o digest da imagem

`scripts/code-version.sh` usa o sha256 dos `RootFS.Layers` (os `diff_ids` das
camadas). A escolha óbvia — o digest que `docker image inspect` reporta em
`.Id` — não serve: com o containerd image store esse campo é o digest do índice
OCI, que embute a atestação de proveniência e **muda a cada build mesmo sem
mudança nenhuma no código**. Dois builds idênticos deram `a65a0f49` e
`e422db0a`. Os `diff_ids` não carregam timestamp: builds iguais dão o mesmo
valor, e qualquer mudança de fonte muda o valor.

O `imageID` que o pod reporta é o digest da config, um terceiro valor ainda
diferente — por isso a verificação do `make smoke` compara `CODE_VERSION`, e
não os digests.

### Limitação conhecida deste identificador

Os `diff_ids` cobrem o sistema de arquivos, não a config da imagem. Uma
mudança no `Dockerfile` que mexa **só em metadado** (`ENV`, `CMD`, `WORKDIR`,
`ENTRYPOINT`) não cria camada nova, então o `code_version` não muda e o Helm
não faz rollout. Verificado: trocar `ENV WORKERS=1` por `ENV WORKERS=2` deixou
o hash em `d00983c04d95`. Mudança de código-fonte sempre passa pelo `COPY`, que
é camada — o caso comum está coberto. Ao mexer em metadado do `Dockerfile`,
force o rollout:

```bash
kubectl -n aes rollout restart deployment/aes-api-api deployment/aes-api-worker
```

______________________________________________________________________

## 2. A API key de bootstrap ficava irrecuperável depois de qualquer `make deploy` (corrigido)

**Estado:** corrigido por `make reissue-key`.

### Sintoma

`make creds` imprimia `AES_RUBRIC_ID` e `AES_PROMPT_TEMPLATE_ID`, mas não a
chave, sem dizer por quê. Qualquer requisição respondia
`{"detail":"Invalid API key"}`, e não havia como recuperar o valor.

### Mecanismo

O seed emite a chave uma única vez e a imprime no stdout do Job; `make creds`
lê dos logs desse Job. O hash armazenado é scrypt com salt por linha,
irrecuperável por construção — o valor existe apenas naquela saída.

O Job roda como hook `post-install,post-upgrade`, então **todo `make deploy` o
recria**. O Job novo encontra a chave existente, não reemite (idempotência
deliberada, coberta por teste), e seu log já nasce sem a linha da chave. O log
anterior morre com o Job antigo.

Ou seja: a chave era legível apenas entre a primeira emissão e o deploy
seguinte. Depois disso, existia no banco e era inalcançável.

### Correção aplicada

- `make reissue-key` apaga a linha `bootstrap`, redeploya para o seed reemitir,
  e imprime a chave nova. Usuário, banco e senha saem do Secret `aes-api-env`,
  não estão fixos no alvo.
- `make creds` deixou de ser silencioso: quando a chave não está no log, ele
  diz que ela já foi emitida e aponta o `make reissue-key`.
- `scripts/smoke.sh` também deixou de morrer calado nesse caso: o `grep` vazio
  disparava o `set -e` antes da linha que explicava o problema, então o smoke
  saía com código 1 e nenhuma mensagem.

Continua valendo guardar a chave assim que ela aparecer: `reissue-key` a
imprime, mas o próximo `make deploy` recria o Job do seed e o valor some do log
outra vez. Isso é inerente ao hash scrypt, não um resquício do bug.

A alternativa de o seed gravar a chave num Secret do Kubernetes continua
descartada: exigiria `kubectl` na imagem da aplicação mais ServiceAccount, Role
e RoleBinding. `reissue-key` resolve o atrito real sem essa superfície.

______________________________________________________________________

## Ao diagnosticar o cluster

Quatro camadas podem reportar sucesso simultaneamente: o `docker build`
conclui, o `kind load` carrega, o `helm upgrade` responde `deployed`, e a API
responde `200`. Nenhuma mente — cada uma está correta no seu escopo. Com a
correção acima o desvio não deveria mais acontecer, e `make smoke` o detecta;
para verificar à mão que o pod é o esperado:

```bash
kubectl -n aes get pod -l app=aes-api-api \
  -o jsonpath='{.items[0].spec.containers[0].env[?(@.name=="CODE_VERSION")].value}'
scripts/code-version.sh
```

Um detalhe que custou tempo: o estágio `prod` do `backend/Dockerfile` define
`WORKDIR /app/src`. Ao inspecionar arquivos dentro do container, o caminho do
módulo é `modules/aes/...`, não `src/modules/aes/...`.

______________________________________________________________________

## O Textract não lê manuscrito em português

**Estado:** contornado por `AES_OCR_PROVIDER=bedrock_vision`, à espera da
verificação da conta AWS.

Medido com 28 redações reais de uma turma de 9º ano: a confiança média do
Textract ficou em **65,1%**, com 97 de 99 palavras classificadas como
`HANDWRITING`, e saídas como `Sigumdo D ridogão puizo par thair Favoro`. O
cabeçalho **impresso** das mesmas folhas — nome da escola, código da BNCC,
nome do aluno — saiu perfeito.

A causa está na documentação da AWS, não na qualidade do material: o Textract
lê texto impresso em seis idiomas, português incluído, mas *"Handwriting,
Invoices and Receipts, Identity documents and Queries processing are in English
only"*. Manuscrito é só inglês. Os erros são anglófonos — `porque` vira
`Pargue`, `sou` vira `san` —, porque o modelo tenta encaixar cursiva portuguesa
num alfabeto que não é o do corpus.

Não há ajuste que resolva. Verificado: `AnalyzeDocument` com `LAYOUT` devolve
texto byte a byte idêntico ao `DetectDocumentText`, então não existe engine
separada para manuscrito. Melhorar resolução ajuda no geral (a AWS recomenda ao
menos 150 DPI), mas não muda o idioma do modelo.

### Contorno

`BedrockVisionProvider` manda a imagem ou o PDF a um modelo multimodal via
Converse, que não tem essa restrição de idioma. Selecionado por
`ocr_provider = "bedrock_vision"` no OpenTofu; o modelo sai de
`vision_model_id`, hoje `us.xai.grok-4.6`.

A transcrição continua sendo gravada em `submissions.raw_text` em vez de a
imagem ir direto ao corretor. Isso é deliberado: a seção 3.7 do TCC exige que o
professor consiga ver **o texto que foi avaliado**, e passar a imagem direto ao
modelo de correção deixaria a nota sem lastro auditável.

O prompt de transcrição proíbe explicitamente corrigir ortografia e
concordância. Um modelo que "arruma" o texto do aluno faria o critério
`adequacao_ling` avaliar a escrita do modelo, não a do aluno.

______________________________________________________________________

## Itens menores, ainda abertos

- `TASKIQ_ENABLED` existe em `settings.py` e não é lido em lugar nenhum. Config
  morta; decidir entre honrar ou remover — é decisão de produto, não correção,
  e a flag está documentada em cinco páginas.
- Os handlers `except Exception: raise HTTPException(500, ...)` nas rotas engolem
  o traceback. Já existe `CatchAllErrorMiddleware` fazendo log estruturado, então
  a correção é remover os handlers de rota — refactor que toca toda rota.
- A suíte fica instável sob carga concorrente do Docker: os testes que usam
  testcontainers podem falhar por contenção do daemon. Não é regressão; roda
  verde isoladamente.
- Os testes da CLI cobrem apenas o modo `local` do gerador de compose; `prod` e
  `nginx` não têm cobertura.
