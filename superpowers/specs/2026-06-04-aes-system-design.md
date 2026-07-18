# Design do Sistema — Plataforma de Correção Assistida de Redações (AES)

Status: aprovado para implementação
Referências: `AGENTS.md`, `TCC engenharia - Arthur Lopes.docx (3).md`

## 1. Contexto e escopo

Este documento detalha a arquitetura técnica da plataforma descrita no TCC "Desenvolvimento de um Sistema Baseado em LLMs para Correção de Redações no Ensino Fundamental". O TCC define um **protótipo acadêmico**: API de submissão assíncrona, rubricas configuráveis, prompts versionados, validação estruturada e rastreabilidade completa das execuções (seções 3.4–3.9 do TCC).

O alvo de produção real desta implementação é Kubernetes (decisão do autor, além do que o TCC exige). O TCC pede apenas "ambiente conteinerizado"; este design usa K8s desde o desenvolvimento local para que a topologia de dev seja a mesma da produção.

**Fora de escopo deste ciclo** (documentar como trabalho futuro na seção 5 do TCC, não implementar agora):

- Autoscaling real de workers e testes de carga com 10 mil redações.
- Deploy em cluster gerenciado (EKS) fora do `kind` local.
- Métricas de concordância com avaliadores humanos (QWK, kappa) — dependem de corpus anotado, ausente nesta etapa (TCC 4.3).

## 2. Domínio

Módulos novos em `backend/src/modules/`, seguindo a convenção vertical-slice já usada por `user`, `tier`, `api_keys`.

### 2.1 Multi-tenancy por município

A plataforma é compartilhada entre municípios (tenants), com isolamento de dados garantido no banco, não só por convenção na aplicação:

- **`Municipio`** (novo) — `id`, `nome`, `monthly_token_budget` (opcional, teto de gasto mensal).
- `User` (módulo já existente) ganha `municipio_id` — um professor pertence a exatamente um município. `is_superuser` (já existente) é o único papel com acesso cross-tenant, para operação da plataforma.
- **Toda tabela do domínio AES** (`EssayPrompt`, `Batch`, `Submission`, `CorrectionJob`, `CorrectionAttempt`, `CorrectionResult`) carrega sua própria coluna `municipio_id`, preenchida automaticamente a partir do registro pai na criação (ex.: `Submission` herda o `municipio_id` do `Batch`). `Rubric` e `PromptTemplate` têm `municipio_id` **anulável**: `NULL` = padrão da plataforma (ex. rubrica BNCC-base, compartilhada), preenchido = customização própria do município.
- **Row-Level Security (RLS) do PostgreSQL** em cada uma dessas tabelas — não apenas filtro na aplicação. Política: `municipio_id = current_setting('app.municipio_id')::int OR current_setting('app.is_superuser', true)::boolean`. Uma dependência na camada de requisição (estende o padrão de auth já existente em `infrastructure/auth`) executa `SET LOCAL app.municipio_id = ...` a partir do usuário autenticado — nunca de um header ou parâmetro controlado pelo cliente — com escopo restrito à transação da requisição. Isso garante isolamento mesmo se uma query da aplicação esquecer o filtro.
- Controle de custo: `Municipio.monthly_token_budget` é checado antes de enfileirar um novo job, somando `tokens_in+tokens_out` do período atual (join `CorrectionAttempt → CorrectionJob → Batch`). Acima do limite, a submissão é rejeitada com erro claro — não é um sistema de billing completo, só um teto de gasto.
- Teste dedicado (module de tenancy): tenant A tenta ler dado de tenant B via ORM sem nenhum filtro explícito — deve retornar zero linhas. É a prova de que a garantia de isolamento funciona no banco, não apenas no comportamento esperado da aplicação.
- Alternativa considerada e descartada: schema ou banco separado por município. Multiplicaria migração/Helm por tenant sem ganhar isolamento além do que RLS já garante.

### 2.2 Entidades

- **`EssayPrompt`** — proposta de redação: enunciado, ano escolar (6º–9º), gênero textual, `support_texts` (lista de textos de apoio/motivadores anexados pelo professor — extensão além do que o TCC descreve, mas alinhada à literatura citada nele sobre uso de referências aplicáveis), referência à `Rubric` ativa. Escopada por `municipio_id` (RLS).

- **`Rubric`** (versionada, imutável após criação) — os 5 critérios fixos do `AGENTS.md`: `adequacao_tema`, `estrutura_textual`, `coesao_coerencia`, `adequacao_ling`, `vocabulario`. Cada critério tem descritor, escala de pontuação e peso. Qualquer alteração cria nova versão (TCC 3.5, 3.9). `municipio_id` anulável (ver 2.1).

- **`PromptTemplate`** (versionado, imutável) — template de instrução enviado ao LLM; monta dinamicamente com redação do aluno, proposta, textos de apoio, rubrica ativa e formato de saída esperado. `municipio_id` anulável (ver 2.1).

- **`Batch`** — lote de submissão. Escopado por `municipio_id` (RLS).

- **`Submission`** — redação individual (texto ou imagem) dentro de um lote; referência ao objeto original no storage S3-compatível. Escopada por `municipio_id` (RLS).

- **`CorrectionJob`** — unidade de processamento assíncrono por submissão: estado (`pending`/`processing`/`done`/`failed`), condição experimental (provedor + modelo + versão de prompt + versão de rubrica + parâmetros de inferência). Escopado por `municipio_id` (RLS).

- **`CorrectionAttempt`** — uma linha por tentativa de correção de um `CorrectionJob` (1:N). Escopada por `municipio_id` (RLS). É o registro de execução exigido pelo TCC 3.7/3.9:

  | Campo                                   | Descrição                                               |
  | --------------------------------------- | ------------------------------------------------------- |
  | `attempt_number`                        | ordem da tentativa                                      |
  | `provider`, `model`                     | condição experimental exata                             |
  | `prompt_version`, `rubric_version`      | versões usadas                                          |
  | `inference_params`                      | temperatura, max_tokens etc.                            |
  | `tokens_in`, `tokens_out`, `latency_ms` | uso e desempenho, extraídos da resposta do provedor     |
  | `raw_response_ref`                      | ponteiro para o storage (resposta bruta)                |
  | `validation_errors`                     | falhas de validação contra o schema Pydantic, se houver |
  | `outcome`                               | `success` / `retry` / `failed`                          |
  | `error_message`                         | preenchido em falha                                     |
  | `created_at`                            | timestamp                                               |

- **`CorrectionResult`** — nota por critério, justificativa vinculada ao texto e feedback acionável; referencia o `CorrectionAttempt` que efetivamente originou o resultado. Escopado por `municipio_id` (RLS). Isso permite reconstruir, para qualquer correção, a cadeia completa de tentativas (inclusive as que falharam) até o resultado aceito.

### 2.3 API

```
POST   /api/v1/essay-prompts          # professor cria proposta + rubrica + textos de apoio
POST   /api/v1/jobs                   # submissão de lote (texto e/ou imagem)
GET    /api/v1/jobs/{job_id}
GET    /api/v1/jobs/{job_id}/results
GET    /api/v1/models                 # provedores/modelos disponíveis
GET    /api/v1/health
```

Toda resposta de resultado inclui `requires_teacher_review: true` fixo (não é uma flag desligável) — reforça que o sistema é assistivo, conforme `AGENTS.md`.

## 3. Fluxo assíncrono e provedores

```
POST /jobs → valida → grava original no storage S3-compatible
           → cria Submission + CorrectionJob (status=pending)
           → enfileira via Taskiq (broker: taskiq-aio-sqs → SQS real / SQS do LocalStack)

Worker Taskiq → carrega job
             → se imagem: OCRProvider.extract_text() → grava transcrição no storage
             → CorrectionProvider.correct(texto, prompt, rubrica, params)
             → valida saída estruturada com Pydantic
             → grava CorrectionAttempt (sucesso ou falha)
             → sucesso: CorrectionResult + job.status=done
             → falha: retry até limite configurado (cada tentativa = nova linha)
```

**Broker**: `taskiq-aio-sqs` (mantido, async, aiobotocore) permite usar Taskiq — já adotado no boilerplate — apontando diretamente para SQS, resolvendo a exigência de fila SQS do TCC (3.6) sem uma ponte adicional.

**Provedores como `Protocol`, configuráveis por lote/job (não globais)** — isso viabiliza o desenho experimental do TCC (3 rodadas por condição, condições distintas por provedor/modelo):

- `CorrectionProvider`: `BedrockProvider`, `OpenRouterProvider`, `MockProvider`. Cada resposta devolve texto bruto, candidato estruturado, `tokens_in`/`tokens_out`, latência.
- `OCRProvider`: `TextractProvider`, `MockOCRProvider`.

**Default local e em testes automatizados: `MockProvider`/`MockOCRProvider`** — determinístico, gratuito, sem chamada de rede (exigência do `AGENTS.md`). Chamada real a Bedrock/OpenRouter só ocorre com credencial explícita configurada; OpenRouter oferece modelos gratuitos (sufixo `:free`) úteis para smoke test manual sem custo.

## 4. Observabilidade

- **Logs estruturados** — reaproveita `infrastructure/logging` já existente; cada log de job carrega `job_id`, `submission_id`, `municipio_id`, `provider`, `model`, `prompt_version`, `rubric_version` como campos estruturados.
- **Métricas Prometheus** (`/metrics` via `prometheus-fastapi-instrumentator`): contagem de jobs por status/provedor/modelo, histograma de latência, contagem de erros/retries por provedor, falhas de OCR.
- **Métricas de uso de LLM**: histograma de `tokens_in`/`tokens_out` por `provider`+`model`, agregado a partir da tabela `CorrectionAttempt` (sem duplicar dado) — permite comparar custo/consumo entre condições experimentais, alinhado à justificativa de controle de custo do próprio TCC (3.6). Tabela de preço por modelo (config estática) converte tokens em custo estimado.
- Subchart opcional `prometheus` + `grafana` (comunidade, grátis) no Helm chart local para visualização — não obrigatório para rodar testes.

## 5. Storage e persistência

- **PostgreSQL** via SQLAlchemy async + Alembic (padrão já existente no boilerplate) para todas as entidades relacionais acima.
- **Storage S3-compatible** (Amazon S3 em produção, LocalStack em dev/test) para: submissão original (texto ou imagem), transcrição de OCR, resposta bruta de cada `CorrectionAttempt`.

## 6. Infraestrutura local em K8s

- Cluster `kind` de desenvolvimento.
- Helm chart do projeto (`deploy/helm/aes-api/`):
  - `api` (Deployment + Service), `worker` (Deployment).
  - `postgres` (chart community, grátis).
  - `localstack` (chart oficial) — emula S3, SQS e Textract.
  - `prometheus` + `grafana` (subchart opcional).
- **LocalStack exige token de auth mesmo no free tier** desde que a Community Edition standalone foi descontinuada (mar/2026). Como projeto acadêmico, usar o plano gratuito para estudantes (verificado via GitHub). Passo de setup explícito na documentação: criar conta, gerar token, colocar em K8s Secret.
- **Sem live-reload** (decisão explícita): iterar código é build da imagem + `kind load docker-image` + `kubectl rollout restart`. Evita adicionar Tilt/Skaffold como nova dependência de dev.
- CLI `bp` ganha um subcomando novo (ex.: `bp deploy generate k8s`) que gera/aplica o Helm chart, seguindo o padrão já existente de `bp deploy generate local/prod`.
- Migrações Alembic rodam como `Job`/`initContainer` do Helm, mesmo padrão do container `migrate` já usado no Docker Compose do boilerplate.

## 7. Testes

- **Unit tests**: sempre `MockProvider`/`MockOCRProvider`, nenhuma dependência de rede ou chave real.
- **API tests**: criação de essay-prompt, submissão de lote, consulta de job/results, casos de erro de validação.
- **Worker tests**: idempotência (reprocessar o mesmo job não duplica resultado), retry até o limite, cada tentativa gera um `CorrectionAttempt`.
- **Migration tests**: `alembic upgrade head` limpo a partir de zero, checado em CI.
- Testes marcados `@pytest.mark.integration` podem rodar contra LocalStack real quando disponível, para validar fila/storage de fato — não são obrigatórios no CI comum.

## 8. Segurança e privacidade (LGPD)

- **Isolamento entre municípios garantido por Row-Level Security no PostgreSQL** (ver 2.1), não apenas por filtro na aplicação — vazamento de dado entre tenants exigiria contornar uma política do próprio banco, não só um bug de query.
- Corpus de teste sintético ou anonimizado — nunca dado real de aluno em fixtures.
- Logs nunca contêm o texto da redação nem PII — apenas metadados (`job_id`, `municipio_id`, `provider`, tokens, timestamps).
- Segredos (chaves Bedrock/OpenRouter, token LocalStack) via K8s Secret; nunca em texto plano no chart ou no repositório.
- Toda resposta de correção é explicitamente assistiva (`requires_teacher_review: true`), nunca apresentada como nota final autônoma.

## 9. Documentação a produzir

- Este documento (`superpowers/specs/2026-06-04-aes-system-design.md`).
- `superpowers/plans/2026-06-04-aes-api.md` — plano de implementação (próximo passo).
- `docs/getting-started/` — setup do cluster `kind`, LocalStack + token de estudante, Helm chart, variáveis de ambiente por provedor.
