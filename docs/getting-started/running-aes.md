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
- An AWS account and a local profile (default `tcc`). OpenTofu provisions an S3
  bucket and an IAM role there, and Textract runs on real AWS — LocalStack does
  not emulate it. See [Textract and the assumed role](#11-textract-and-the-assumed-role).

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

## 5b. Using a real LLM provider

The stack defaults to the `mock` correction provider — deterministic, free, and
what every automated test uses. To run a correction against a real model, put a
key in `infra/terraform.tfvars` and re-run `make infra`:

```hcl
groq_api_key = "gsk_..."
```

Then submit a job naming that provider:

```bash
curl -s "${AUTH[@]}" -X POST "$API/api/v1/aes/jobs" -d '{..., "provider": "groq", "model": "llama-3.3-70b-versatile"}'
```

`GET /api/v1/aes/models` reports which providers have credentials
(`available: true`) without making a network call.

Presets ship for these gateways, all OpenAI-compatible and all offering a
no-credit-card free tier as verified on **2026-09-05** — free tiers change
often, so check before relying on one:

| provider | gateway | notes |
| --- | --- | --- |
| `openrouter` | OpenRouter | the default choice; use a `:free` model suffix |
| `groq` | Groq | fastest free inference; ~30 req/min, 1,000 req/day |
| `cerebras` | Cerebras | highest daily volume (~1M tokens/day) |
| `github` | GitHub Models | free with a GitHub account; widest model catalogue |
| `gemini` | Google AI Studio | a non-Llama model family, useful for comparison |

Model names come from `{PROVIDER}_MODEL` settings and can be overridden per job.

**Cerebras caveat:** structured-output support there is model-dependent — some
models reject `tools` and `response_format` together, which surfaces as a
`validation_error` on every attempt rather than a correction. If that happens,
switch the model rather than the gateway.

Adding another OpenAI-compatible gateway is a `base_url` entry in
`GATEWAY_BASE_URLS` (`backend/src/modules/aes/providers/openai_compatible.py`)
plus its key/model settings — no new provider class.

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

## 11. Textract and the assumed role

OCR runs on real AWS Textract. The pods hold **no AWS credentials** — not an
access key, not a mounted `~/.aws`. They authenticate the way a workload on EKS
would, and every piece of it is provisioned by OpenTofu.

### Why this is not just a key in a Secret

`kind` is not EKS, so IRSA is unavailable. The alternative would be a static
access key living in the cluster and in the Tofu state. Instead the cluster acts
as its own OIDC identity provider:

1. `modules/oidc-issuer` creates a public S3 bucket and publishes an OpenID
   discovery document there. The name is a truncated SHA-256 of your AWS account
   id — deterministic, so the issuer stays stable and is known at plan time, but
   the account id does not sit in clear text on a public bucket. Treat that hash
   as obfuscation, not a secret: an account id is 12 digits, so anyone holding
   the bucket name can reverse it by brute force.
2. The `kind` cluster is created with `service-account-issuer` pointing at that
   bucket, so every service account token it mints carries that issuer.
3. `modules/oidc-trust` reads the cluster's public signing keys from
   `/openid/v1/jwks`, publishes them as `keys.json`, registers the bucket as an
   IAM OIDC provider, and creates the role `aes-api-textract` — trusted only for
   `system:serviceaccount:aes:aes-api` with audience `sts.amazonaws.com`, and
   allowed only `textract:DetectDocumentText`.
4. The chart mounts a projected service account token at
   `/var/run/secrets/aws/token`. Given `AWS_ROLE_ARN` and
   `AWS_WEB_IDENTITY_TOKEN_FILE`, boto3 calls `AssumeRoleWithWebIdentity` on its
   own and refreshes the credentials as the kubelet rotates the token.

The bucket is public on purpose and holds only public signing keys and a
discovery document — the same material any OIDC provider serves openly. It holds
no secret.

To confirm the pod is running as the role rather than as a user:

```bash
kubectl -n aes exec deploy/aes-api-api -- \
  python -c "import boto3; print(boto3.client('sts').get_caller_identity()['Arn'])"
```

It should print an `assumed-role/aes-api-textract/...` ARN.

### Accepted formats

`POST /api/v1/aes/jobs/images` takes JPEG, PNG and **single-page PDF**, up to
10 MB each and 50 per batch, mixed freely in one request — a scanned essay
usually arrives as a one-page PDF.

Textract's synchronous `DetectDocumentText` reads a one-page PDF but rejects a
multi-page one with `UnsupportedDocumentException`. The API does not count pages
before accepting the file — that would mean carrying a PDF parser just for the
check — so a multi-page upload is accepted and the job fails, with that error
recorded in `correction_attempts.error_message`. Supporting multi-page essays
means moving to Textract's asynchronous API, which reads from a real S3 bucket
rather than from bytes.

### Switching OCR off

Set `ocr_provider = "mock"` in `infra/terraform.tfvars` and re-run `make infra`.
The mock returns a fixed string and never touches AWS, so image submissions
still exercise upload, storage, queue and correction — just not transcription.

!!! warning "Replacing the cluster needs two runs"
    The issuer is baked into the kubeadm config, so changing it replaces the
    `kind` cluster. Terraform refreshed the `kubernetes_*` resources before that
    replacement, so the first run fails with `secrets "aes-api-env" not found`.
    Run it again and it converges — the second run sees the resources are gone
    and recreates them. A fresh `make up` can also fail once on
    `no matches for kind "ServiceMonitor"`, when the chart is applied before
    kube-prometheus-stack finishes installing its CRDs; the same retry fixes it.

!!! danger "Textract is not free and handwriting is the hard case"
    `DetectDocumentText` costs about US$1.50 per 1000 pages. More importantly,
    it is document OCR: printed text transcribes cleanly, but a
    Ensino Fundamental student's handwriting is the worst case for this class of
    model. The transcription quality becomes the ceiling for the whole
    correction, which is worth measuring rather than assuming.
