# Local Kubernetes development

This project's local dev loop runs on `kind` (Kubernetes-in-Docker), matching the
production deployment target described in `superpowers/specs/2026-06-04-aes-system-design.md`.
There is no live-reload — after editing code you rebuild the image and reload it into
the cluster (see step 5).

## 1. Prerequisites

- Docker
- `kind` (https://kind.sigs.k8s.io/) — not preinstalled on most dev machines; if
  `kind version` fails, install a released binary without sudo:
  ```bash
  curl -Lo /tmp/kind https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64
  chmod +x /tmp/kind
  mv /tmp/kind ~/.local/bin/kind   # any directory already on PATH works
  ```
  (use `kind-linux-arm64` / `kind-darwin-amd64` / `kind-darwin-arm64` as needed)
- `kubectl`
- `helm`

## 2. Start the cluster

```bash
make cluster-up
make cluster-status   # confirms kube-system pods are Running
```

## 3. Get a LocalStack auth token

LocalStack retired its standalone Community Edition in March 2026 — every tier,
including the free one, now requires an auth token. As a student project, use the
LocalStack student plan (verify with your GitHub account) at
https://app.localstack.cloud, then export the token:

```bash
export LOCALSTACK_AUTH_TOKEN=<your-token>
```

## 4. Build and load the app image

The chart never pulls from a registry — `values.yaml` points both the API and the
worker at `aes-api-api:local`, an image that must already exist inside the kind
node before `helm install` runs, or every pod (and the migration Job) sits in
`ImagePullBackOff`/`ErrImageNeverPull` forever.

```bash
docker build -t aes-api-api:local backend/
kind load docker-image aes-api-api:local --name aes-local
```

## 5. Generate the chart, create the env Secret, install

```bash
uv run bp deploy generate k8s
helm dependency update deploy/helm/aes-api
```

**Known limitation:** the chart is a scaffold — the API Deployment, worker
Deployment, and the pre-install migration Job all reference an
`{{ "{{ .Release.Name }}" }}-env` Secret via `envFrom`, but nothing in the chart
creates that Secret. Without it, every pod fails with `CreateContainerConfigError`.
Create it before `helm install` (release name `aes-api` used throughout this doc):

```bash
kubectl create secret generic aes-api-env \
  --from-literal=POSTGRES_SERVER=aes-api-postgresql \
  --from-literal=POSTGRES_USER=aes_app \
  --from-literal=POSTGRES_PASSWORD=aes_app \
  --from-literal=POSTGRES_DB=postgres \
  --from-literal=AES_STORAGE_ENDPOINT_URL=http://aes-api-localstack:4566 \
  --from-literal=CACHE_BACKEND=memory \
  --from-literal=SESSION_BACKEND=memory \
  --from-literal=RATE_LIMITER_ENABLED=false \
  --from-literal=TASKIQ_BROKER_TYPE=sqs \
  --from-literal=TASKIQ_SQS_ENDPOINT_URL=http://aes-api-localstack:4566 \
  --from-literal=TASKIQ_SQS_QUEUE_URL=http://aes-api-localstack:4566/000000000000/default \
  --from-literal=AES_OCR_PROVIDER=mock \
  --from-literal=SESSION_SECURE_COOKIES=false \
  --from-literal=PRODUCTION_SECURITY_VALIDATION_ENABLED=false
```

The `CACHE_BACKEND`/`SESSION_BACKEND`/`RATE_LIMITER_*` overrides exist because the
chart only ships Postgres and LocalStack as dependencies (see `Chart.yaml`) — there
is no Redis or memcached in this cluster, yet those three subsystems default to
`redis`/`memcached`. `memory` is the in-process backend (`CacheBackend`/
`SessionBackend` enums in `backend/src/infrastructure/config/enums.py`); it's
correct for `replicas: 1` but won't survive a pod restart or scale past one
replica. `AES_STORAGE_ACCESS_KEY`/`AES_STORAGE_SECRET_KEY` don't need overriding —
they already default to `test`/`test`, which is what LocalStack accepts.
`AES_OCR_PROVIDER=mock` sidesteps the fact that Textract emulation requires a
LocalStack Pro-tier feature the student plan may not include — check your plan
before setting this to `textract`. Check
`backend/src/infrastructure/config/settings.py` for the full list of settings the
app reads and add any others your setup needs — this list is not exhaustive.

```bash
helm install aes-api deploy/helm/aes-api \
  --set localstack.authToken=$LOCALSTACK_AUTH_TOKEN
kubectl get pods -w   # wait for aes-api-migrate to complete, then api/worker Running
```

This installs Postgres, LocalStack (emulating S3, SQS, Textract), the API, the
Taskiq worker, and runs Alembic migrations as a pre-install Helm hook.

## 6. Provision LocalStack resources

LocalStack starts empty — nothing in the chart creates the S3 bucket or SQS queue
the app expects. Create both after the LocalStack pod is `Running`:

```bash
kubectl port-forward svc/aes-api-localstack 4566:4566 &

AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
  aws --endpoint-url=http://localhost:4566 s3 mb s3://aes-submissions

AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 \
  aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name default
```

The queue URL printed back must match `TASKIQ_SQS_QUEUE_URL` in the Secret from
step 5 (in-cluster form, using the Service name, not `localhost`) — if LocalStack
assigns a different account id than `000000000000`, update the Secret and
`kubectl rollout restart deployment/aes-api-worker`.

## 7. Verify

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/metrics
```

## 8. Iterate on code

There is no live-reload in the cluster. After a code change, repeat step 4's
build/load, then:

```bash
kubectl rollout restart deployment/aes-api-api deployment/aes-api-worker
```

## 9. Tear down

```bash
helm uninstall aes-api
make cluster-down
```
