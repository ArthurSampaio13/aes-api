# Local Kubernetes development

This project's local dev loop runs on `kind` (Kubernetes-in-Docker), matching the
production deployment target described in `superpowers/specs/2026-06-04-aes-system-design.md`.
There is no live-reload — after editing code you rebuild the image and reload it into
the cluster (see step 5).

## 1. Prerequisites

- Docker
- `kind` (https://kind.sigs.k8s.io/)
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

## 4. Generate and install the Helm chart

```bash
uv run bp deploy generate k8s
helm dependency update deploy/helm/aes-api
helm install aes-api deploy/helm/aes-api \
  --set localstack.authToken=$LOCALSTACK_AUTH_TOKEN
```

This installs Postgres, LocalStack (emulating S3, SQS, Textract), the API, the
Taskiq worker, and runs Alembic migrations as a pre-install Helm hook.

## 5. Iterate on code

There is no live-reload in the cluster. After a code change:

```bash
docker build -t aes-api-api:local backend/
kind load docker-image aes-api-api:local --name aes-local
kubectl rollout restart deployment/aes-api-api deployment/aes-api-worker
```

## 6. Verify

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/metrics
```

## 7. Tear down

```bash
helm uninstall aes-api
make cluster-down
```
