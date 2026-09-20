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
- An OpenRouter API key. Both OCR and correction run through OpenRouter — add
  the key to `infra/terraform.tfvars`, nothing else to provision.

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

`up` chains `infra`, `deploy` (which pulls in `build` and `kind-load`), and
`creds`:

| Target      | What it does                                                                 |
| ----------- | ----------------------------------------------------------------------------- |
| `infra`     | `tofu apply` — creates the `kind` cluster, Postgres, LocalStack, the app Secret, and the Prometheus/Grafana stack |
| `build`     | `docker build -f backend/Dockerfile -t aes-api:dev .` — builds the app image from the repo root. A prerequisite of `deploy`; you rarely call it directly |
| `kind-load` | Loads that image into the `kind` cluster's nodes. Also a prerequisite of `deploy` |
| `deploy`    | `helm upgrade --install` — runs the Alembic migration Job, then the API and worker Deployments, then the seed Job. Waits for both rollouts to converge, then copies the bootstrap key into a Secret |
| `creds`     | Prints the API URL, the seeded IDs, and the bootstrap API key                 |

Two more you will want later:

| Target        | What it does                                                               |
| ------------- | -------------------------------------------------------------------------- |
| `smoke`       | End-to-end check: asserts the pods run your locally built image, then drives a full correction through the API |
| `reissue-key` | Drops the bootstrap API key and issues a fresh one — see [What you get](#4-what-you-get) |

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
| API key        | A bootstrap API key issued for the demo município, copied into the `aes-api-bootstrap-key` Secret so it survives redeploys |
| Rubric         | Version 1, the five fixed criteria from `AGENTS.md`                   |
| Prompt template | Version 1                                                             |

Get the API URL and credentials at any time with:

```bash
make creds
```

!!! note "The API key only prints once"
    The seed Job detects an existing bootstrap key on a repeat `make deploy`
    and does not reissue it — so `make creds` on a second run will not show a
    key line. That is fine: `make deploy` copies the key into a Secret
    (`aes-api-bootstrap-key`) the moment the seed issues it, and `make creds`
    reads it back from there, so the value survives any number of redeploys.
    If the key is genuinely gone — you deleted the Secret, or the row predates
    this mechanism — run `make reissue-key`: it drops the `bootstrap` row and
    the Secret, redeploys so the seed issues a fresh key, and prints it. Do not `make down && make up` to "fix" this — that destroys
    the Postgres volume, every generated password, and the Tofu state, just to
    recover a string.

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

**Get the batch manifest** — every condition behind every correction in the
batch: provider, model, prompt/rubric versions, tokens, cost, guardrail
verdicts, and the transcription trace:

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/aes/batches/<BATCH_ID>/manifest
```

`<BATCH_ID>` is the `batch_id` returned by the submit call above. This is the
audit trail a researcher or a municipality would export to compute
cost-per-correction or reproduce a run.

## 5b. Using a real LLM provider

The stack defaults to the `mock` correction provider — deterministic, free, and
what every automated test uses. Real corrections go through **OpenRouter**, the
only network provider. Put the key in `infra/terraform.tfvars` and re-run
`make infra`:

```hcl
openrouter_api_key = "sk-or-..."
```

Then submit a job naming the provider and the model:

```bash
curl -s "${AUTH[@]}" -X POST "$API/api/v1/aes/jobs" \
  -d '{..., "provider": "openrouter", "model": "deepseek/deepseek-v4.1-flash"}'
```

The `model` is the OpenRouter id verbatim, `vendor/model`. It is checked
against the live catalogue at submission, so a typo returns 422 immediately
instead of burning a queued job on a call that was never going to work. If the
catalogue is unreachable the model is accepted rather than blocking submissions
on a third party being down.

Omitting `model` falls back to `OPENROUTER_MODEL` (tofu variable `openrouter_model`).

### Which models are available

```bash
curl -s -H "X-API-Key: $API_KEY" "$API/api/v1/aes/models"
```

This mirrors the OpenRouter catalogue — roughly 300 entries with `id`, input
modalities and price, cached for an hour. Filter it when you need a model that
reads images:

```bash
curl -s -H "X-API-Key: $API_KEY" "$API/api/v1/aes/models?input_modality=image"
```

That filter matters for transcription: about 275 of the models accept images,
and picking one of the rest fails only after the job is already running.

### Transcribing handwriting

`AES_OCR_PROVIDER` takes `mock` or `vision`. The `vision` provider sends the
page straight to a multimodal model through the same OpenRouter path, so a
scanned image and a single-page PDF are handled the same way.

Its prompt forbids correcting spelling, accentuation and agreement. That
prohibition is load-bearing rather than cosmetic: a model that tidies up the
student's text would make the `adequacao_ling` criterion grade the model's
writing instead of the student's, inflating the score with no trace of it.

## 5c. Seeing the cluster in kubectx

`make` pins `KUBECONFIG` to `~/.kube/kind-aes-local.yaml`, written by OpenTofu,
and deliberately does not read the one from your shell. The assignment is `=`,
not `?=`, so no target here can be redirected at whatever context happens to be
selected — including a production EKS.

The cost is that `kubectx` never sees the cluster, and it reads a single file,
so listing both paths in `KUBECONFIG` fails with *multiple files in KUBECONFIG
are currently not supported*.

```bash
make kubectx
```

That merges only the kind context into `~/.kube/config`, leaving every other
context untouched, and it is safe precisely because the Makefile pins its own
path. The context is called `kind-aes-local`.

Re-run it after recreating the cluster: the API server certificate changes, and
the merged context goes stale.

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
make deploy
```

`deploy` depends on `build` and `kind-load`, so one target covers the whole
loop. Both steps matter: the nodes cache images by tag, so without
`kind-load` the pods keep the old code; and `helm upgrade` only rolls pods
when the rendered manifest changes, which is why `codeVersion` is derived
from the image content rather than from the git SHA.

`make smoke` asserts the running pod's `CODE_VERSION` matches the locally
built image, so a stale deploy fails loudly instead of passing.

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
: The image was built but never loaded into the `kind` cluster's nodes. Run
  `make deploy`, which loads it before upgrading the release.

**`make creds` shows the IDs but no API key**
: Neither the `aes-api-bootstrap-key` Secret nor the seed Job's log has it.
  Run `make reissue-key`.
