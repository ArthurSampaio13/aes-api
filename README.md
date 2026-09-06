<h1 align="center">AES-API</h1>

<p align="center" markdown=1>
  <i>Correção assistida de redações do Ensino Fundamental, baseada em LLM — com rubrica configurável, rastreabilidade por tentativa e revisão docente obrigatória.</i>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://opentofu.org"><img src="https://img.shields.io/badge/OpenTofu-FFDA18?style=for-the-badge&logo=opentofu&logoColor=black" alt="OpenTofu"></a>
  <a href="https://kubernetes.io"><img src="https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
</p>

## O que é

Professores do Ensino Fundamental corrigem muitas redações com pouco tempo, e
os alunos recebem feedback esparso e inconsistente. Esta API ataca esse gargalo:
recebe redações em texto ou imagem, processa de forma assíncrona, aplica uma
rubrica versionada e devolve nota, justificativa e sugestão acionável por
critério.

É o artefato de software de um TCC sobre uso de LLMs na avaliação textual.

**O que ele não é:** um corretor autônomo. Toda resposta carrega
`requires_teacher_review: true` — não é uma flag desligável — e o resultado é
ponto de partida para a revisão do professor, não substituto dela. O sistema
não toma decisão de alto impacto sobre nenhum aluno.

Também não há, neste repositório, validação em sala de aula, ganho de
aprendizagem medido ou concordância com avaliadores humanos. O que existe é o
protótipo funcional e sua evidência de execução.

## Rubrica

Cinco critérios fixos, alinhados a competências de escrita no estilo BNCC/SAEB:

| Critério            | Avalia                          |
| ------------------- | ------------------------------- |
| `adequacao_tema`    | aderência ao tema proposto      |
| `estrutura_textual` | estrutura do gênero pedido      |
| `coesao_coerencia`  | articulação entre as ideias     |
| `adequacao_ling`    | adequação à norma escrita       |
| `vocabulario`       | repertório e precisão vocabular |

Cada critério recebe nota, justificativa ancorada em evidência do próprio texto
do aluno, e o resultado traz uma sugestão acionável de melhoria. Rubricas e
templates de prompt são **versionados e imutáveis** — alterar cria uma versão
nova, para que qualquer correção antiga continue reconstruível.

## Como funciona

```
POST /jobs → valida → grava o original no storage S3-compatible
           → cria Submission + CorrectionJob (pending)
           → enfileira via Taskiq/SQS

Worker → se imagem: OCR → transcrição
       → provedor LLM corrige contra rubrica + prompt versionados
       → valida a saída com Pydantic
       → grava CorrectionAttempt (sucesso ou falha)
       → sucesso: CorrectionResult + job done
       → falha: nova tentativa, cada uma sua própria linha
```

**Provedores desacoplados por `Protocol`**, escolhidos por job: `mock`
(determinístico, default em testes), `openrouter` e `bedrock` para correção;
`mock` e `textract` para OCR. Trocar de modelo não exige mexer no worker — é o
que viabiliza comparar condições experimentais.

**Multi-tenancy por município** com Row-Level Security do PostgreSQL. O
isolamento é garantido no banco, sob um papel `NOSUPERUSER NOBYPASSRLS`, e vale
mesmo que uma query da aplicação esqueça de filtrar.

## Rastreabilidade

Cada tentativa de correção grava uma linha própria, com:

`attempt_number` · `provider` · `model` · `prompt_version` · `rubric_version` ·
`inference_params` · `tokens_in` / `tokens_out` · `latency_ms` ·
`code_version` · `raw_response_ref` (resposta bruta no storage) ·
`validation_errors` · `outcome` · `created_at`

Isso permite reconstruir a cadeia completa de uma correção, incluindo as
tentativas que falharam, e é o que torna o resultado auditável e reproduzível.

## Rodando localmente

Pré-requisitos: Docker, [mise](https://mise.jdx.dev) — que pina todo o resto —,
8 GB de RAM, portas 8000 e 3000 livres, e um token da LocalStack (o plano de
estudante sai verificando conta do GitHub em
[app.localstack.cloud](https://app.localstack.cloud)).

```bash
make setup
cp infra/terraform.tfvars.example infra/terraform.tfvars
# preencha localstack_auth_token
make up
```

`make up` leva de nenhum cluster a API respondendo: OpenTofu cria o cluster
`kind` com Postgres, LocalStack (S3 + SQS) e Prometheus/Grafana; o chart Helm
sobe API e worker; as migrations rodam; e um seed cria município de
demonstração, rubrica v1, template de prompt v1 e uma API key.

```bash
make creds    # API key e URLs
make smoke    # fluxo fim a fim, com asserts
make grafana  # dashboard de correções
make down     # destrói tudo
```

Guia completo, passo a passo em curl e solução de problemas em
[`docs/getting-started/running-aes.md`](docs/getting-started/running-aes.md).

## API

```
POST   /api/v1/aes/rubrics
GET    /api/v1/aes/rubrics/{id}
POST   /api/v1/aes/essay-prompts
GET    /api/v1/aes/essay-prompts/{uuid}
POST   /api/v1/aes/jobs               # lote de textos
POST   /api/v1/aes/jobs/images        # lote de imagens (multipart)
GET    /api/v1/aes/jobs/{job_id}
GET    /api/v1/aes/jobs/{job_id}/results
GET    /api/v1/aes/models             # provedores disponíveis
GET    /health
GET    /metrics
```

Autenticação por API key ou sessão, com permissões por recurso. Swagger em
`/docs`.

## Layout

| Caminho                       | Conteúdo                                                        |
| ----------------------------- | --------------------------------------------------------------- |
| `backend/src/modules/aes/`    | domínio da correção: models, providers, worker, rotas           |
| `backend/src/infrastructure/` | auth, banco, cache, filas, logging, RLS                         |
| `backend/migrations/`         | Alembic, com as políticas de RLS                                |
| `infra/`                      | OpenTofu: cluster `kind` e plataforma                           |
| `charts/aes-api/`             | chart Helm da aplicação, com dashboard e ServiceMonitors        |
| `cli/`                        | `bp`, ferramenta de desenvolvimento (compose, auditoria de env) |
| `scripts/smoke.sh`            | teste de fumaça fim a fim                                       |

## Desenvolvimento

```bash
cd backend && uv run pytest          # 418 testes
cd backend && uv run ruff check && uv run mypy src
make build && make kind-load && make deploy   # recarrega o cluster
```

O `kind-load` no meio não é opcional: a tag da imagem não muda e o
`imagePullPolicy` é `IfNotPresent`, então sem ele o cluster segue rodando o
código antigo.

Sem Kubernetes, para iterar mais rápido:

```bash
uv run bp deploy generate local && docker compose up --build
```

## Privacidade

Texto de redação é tratado como dado sensível de estudante. Nenhuma linha de
log carrega conteúdo da redação — há teste automatizado afirmando isso, e os
sinks do Loguru rodam com `diagnose=False` para que tracebacks não vazem
variáveis locais. Exemplos e testes usam redações sintéticas.

## Construído sobre

O [Fastro / FastAPI-boilerplate](https://github.com/benavlabs/FastAPI-boilerplate)
da Benav Labs, que fornece a base de autenticação, CRUD, cache, rate limiting,
filas e o CLI `bp`.

## Licença

[MIT](LICENSE.md)
