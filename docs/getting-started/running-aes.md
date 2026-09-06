# Running AES

AES (the essay-correction API this repo builds) runs locally on the same shape it
targets in production: a Kubernetes cluster. OpenTofu provisions a `kind` cluster
with Postgres, LocalStack and Prometheus/Grafana, an in-tree Helm chart deploys
the app, and a seed job bootstraps a demo tenant. `make up` drives the whole
thing end to end.

## 1. Prerequisites

- Docker
- [`mise`](https://mise.jdx.dev/) — pins every other tool this repo needs
  (`uv`, `pre-commit`, `opentofu`, `kind`, `kubectl`, `helm`, `k9s`,
  `shellcheck`) to the versions it expects. The `Makefile` runs them through
  `mise exec`, so `make` works whether or not `mise` is activated in your
  shell.
- 8 GB of RAM free for the cluster (Postgres, LocalStack, the app, and
  kube-prometheus-stack all run as pods on your machine)
- Ports `8000` and `3000` free on the host (API and Grafana)

Install the pinned tools and the git hooks:

```bash
make setup
```

## 2. LocalStack auth token

LocalStack retired its standalone Community Edition in March 2026 — every tier,
including the free one, now requires an auth token. As a student project, sign
up for the LocalStack student plan (verified via GitHub) at
<https://app.localstack.cloud> and generate a token.

OpenTofu reads the token from `infra/terraform.tfvars`, which is gitignored:

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Add your token to that file:

```hcl
localstack_auth_token = "<your-token>"
```

(An environment variable also works — `TF_VAR_localstack_auth_token=<token>` —
but the `tfvars` file is the documented, repeatable path: nothing to re-export
every time you open a new shell.)

## 3. Bring it up

```bash
make up
```

`up` chains five targets:

| Target      | What it does                                                                 |
| ----------- | ----------------------------------------------------------------------------- |
| `infra`     | `tofu apply` — creates the `kind` cluster, Postgres, LocalStack, the app Secret, and the Prometheus/Grafana stack |
| `build`     | `docker build -f backend/Dockerfile -t aes-api:dev .` — builds the app image from the repo root |
| `kind-load` | Loads that image into the `kind` cluster's nodes                              |
| `deploy`    | `helm upgrade --install` — runs the Alembic migration Job, then the API and worker Deployments, then the seed Job |
| `creds`     | Prints the API URL and the bootstrap credentials from the seed Job's logs     |

!!! warning "First run takes 6–10 minutes"
    Pulling the `kind` node image, the Postgres/LocalStack images, and the
    kube-prometheus-stack chart's images takes most of that time. Subsequent
    `make up` runs are faster since images stay cached.

## 4. What you get

| Component      | State                                                                 |
| -------------- | ---------------------------------------------------------------------- |
| Cluster        | `kind` cluster named `aes-local`                                       |
| Postgres       | Running with an application role `aes_app` (`NOSUPERUSER NOBYPASSRLS`, so Row-Level Security actually holds) |
| LocalStack     | Running with the S3 bucket and SQS queue the app expects              |
| Secret         | `aes-api-env`, wiring the API and worker to Postgres and LocalStack   |
| Prometheus/Grafana | `kube-prometheus-stack`, scraping the API and worker             |
| Schema         | Migrated to `head` by a pre-install Helm hook                         |
| Município (tenant) | A demo município seeded                                          |
| Tier           | A default tier seeded                                                 |
| Superuser      | A first superuser seeded                                              |
| API key        | A bootstrap API key issued for the demo município                     |
| Rubric         | Version 1, the five fixed criteria from `AGENTS.md`                   |
| Prompt template | Version 1                                                             |

Get the API URL and credentials at any time with:

```bash
make creds
```

!!! note "The API key only prints once"
    The seed Job detects an existing bootstrap key on a repeat `make deploy`
    and does not reissue it — so `make creds` on a second run will not show a
    key line. That's expected, not a failure. If you lost the key, read it
    back from the seed Job's own logs:
    `kubectl -n aes logs job/aes-api-seed`. Do not `make down && make up` to
    "fix" this — that destroys the Postgres volume, every generated password,
    and the Tofu state, just to recover a string.

!!! warning "The bootstrap key bypasses tenant isolation"
    The seeded API key belongs to the platform superuser, and
    `aes/dependencies.py` sets the RLS session variable to
    `is_superuser=true` for that user — so Row-Level Security is bypassed for
    every request made with it, including this entire walkthrough and
    `make smoke`. That's acceptable for a single-tenant local demo, but it
    means none of this exercises the tenant-isolation guarantee. That
    guarantee is covered by the automated RLS test suite instead, not by this
    walkthrough.

## 5. End-to-end flow

`scripts/smoke.sh` runs this exact sequence against the live stack (and is
what `make smoke` runs). Set `API_KEY` to the value from `make creds`:

```bash
export API_KEY=<from make creds>
```

**Health check** — no auth required:

```bash
curl -s http://localhost:8000/health
```

```json
{"status": "healthy"}
```

**List available correction models:**

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/aes/models
```

Returns a list of provider/model entries; the local stack always has a
`mock` provider available, since real LLM calls need real credentials.

**Create an essay prompt** (needs the seeded `rubric_id` / `prompt_template_id`
from the seed logs — `make creds` shows the seed logs, or run
`kubectl -n aes logs job/aes-api-seed`):

```bash
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/v1/aes/essay-prompts -d '{
    "titulo": "O rio da minha cidade",
    "enunciado": "Escreva um artigo de opinião sobre a importância de cuidar do rio da sua cidade.",
    "ano_escolar": "9",
    "genero_textual": "artigo de opinião",
    "support_texts": [],
    "rubric_id": <RUBRIC_ID>,
    "prompt_template_id": <PROMPT_TEMPLATE_ID>
  }'
```

Returns the created prompt, including its `uuid`.

**Submit a batch for correction:**

```bash
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/v1/aes/jobs -d '{
    "essay_prompt_uuid": "<PROMPT_UUID>",
    "texts": ["O rio da minha cidade esta muito sujo..."],
    "provider": "mock",
    "model": "mock-v1"
  }'
```

Returns `job_ids`, one `CorrectionJob` per submitted text.

**Poll the job until it's done:**

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/aes/jobs/<JOB_ID>
```

`status` moves from `pending` to `processing` to `done` as the worker picks
it up (or `failed`, if every retry was exhausted).

**Read the result:**

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/aes/jobs/<JOB_ID>/results
```

Returns `scores` for the five fixed criteria (`adequacao_tema`,
`estrutura_textual`, `coesao_coerencia`, `adequacao_ling`, `vocabulario`),
`feedback`, and `sugestao_acionavel`.

!!! note "`requires_teacher_review` is always `true`"
    Every result carries `requires_teacher_review: true`, by design and
    unconditionally. This system is assistive — it never presents a score as
    an autonomous final grade. A teacher reviews every correction before it
    reaches a student.

## 6. Observability

```bash
make grafana
```

prints the Grafana URL, the admin user, and the generated admin password.
Open the **AES — Correções** dashboard:

| Panel                             | Answers                                                        |
| ---------------------------------- | --------------------------------------------------------------- |
| Jobs por status                   | How many `CorrectionJob`s are pending/processing/done/failed     |
| Tentativas por outcome            | How many `CorrectionAttempt`s succeeded, were retried, or failed |
| Latência do provedor (ms)         | How long each provider call takes                                |
| Tokens acumulados por condição    | Token usage grouped by provider+model, for comparing experimental conditions |

The worker runs with `concurrency: 1` deliberately — its Prometheus client
keeps one registry per process, so a single-worker process is what keeps
those metrics complete instead of split across untracked processes.

For interactive pod/log inspection instead of `kubectl` one-liners:

```bash
k9s --kubeconfig ~/.kube/kind-aes-local.yaml
```

## 7. Development loop

There is no live-reload in the cluster. After a code change:

```bash
make build && make kind-load && make deploy
```

`build` rebuilds the image under the same `aes-api:dev` tag; `kind-load` is
not optional here — the cluster's nodes cache images by tag, so skipping it
leaves the pods running the old code even though `helm upgrade` re-applies
the migration Job and restarts the API and worker Deployments.

## 8. Without Kubernetes

To iterate on the backend without touching the cluster at all, generate a
plain Compose stack instead:

```bash
uv run bp deploy generate local
docker compose up --build
```

This gets you the same app with hot-reload, backed by Postgres, Redis and
LocalStack in containers — no `kind`, no Helm. The LocalStack auth token is
still required here: export `LOCALSTACK_AUTH_TOKEN` in your shell before
`docker compose up`, the same token used for the `kind` path.

## 9. Tear down

```bash
make down
```

Destroys everything OpenTofu created and deletes the `kind` cluster.

## 10. Common issues

**`tofu apply` fails asking for `localstack_auth_token`**
: You skipped [step 2](#2-localstack-auth-token) — add the token to
  `infra/terraform.tfvars`.

**Port `8000` or `3000` already in use**
: Something else on the host is bound to the API or Grafana port. Free it, or
  override `api_host_port` / `grafana_host_port` in `infra/terraform.tfvars`
  before `make infra`.

**Cluster pods stuck `Pending` or the machine grinds to a halt**
: Postgres, LocalStack, the app, and kube-prometheus-stack all request memory
  concurrently — under 8 GB free, something won't get scheduled. Close other
  memory-heavy applications and retry.

**Pods stuck in `ImagePullBackOff`**
: The image was built but never loaded into the `kind` cluster's nodes — you
  ran `make build` (or `make deploy`) without `make kind-load` in between.
  Run `make kind-load` and re-run `make deploy`.
