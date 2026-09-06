export KUBECONFIG ?= $(HOME)/.kube/kind-aes-local.yaml

CLUSTER ?= aes-local
MISE := mise exec --

.PHONY: setup infra down status grafana creds smoke reissue-key
.NOTPARALLEL:

setup:
	mise install
	$(MISE) pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

infra:
	$(MISE) tofu -chdir=infra init -upgrade
	$(MISE) tofu -chdir=infra apply -auto-approve

down:
	$(MISE) tofu -chdir=infra destroy -auto-approve
	-$(MISE) kind delete cluster --name $(CLUSTER)
	rm -rf infra/.state

status:
	$(MISE) kubectl get pods -A

grafana:
	@echo "URL:  $$($(MISE) tofu -chdir=infra output -raw grafana_url)"
	@echo "user: admin"
	@echo "pass: $$($(MISE) tofu -chdir=infra output -raw grafana_password)"

creds:
	@echo "API:   $$($(MISE) tofu -chdir=infra output -raw api_url)"
	@echo "Docs:  $$($(MISE) tofu -chdir=infra output -raw api_url)/docs"
	@$(MISE) kubectl -n aes logs job/aes-api-seed 2>/dev/null | grep -E '^AES_(RUBRIC_ID|PROMPT_TEMPLATE_ID)=' \
		|| echo "ids indisponíveis: rode make deploy"
	@KEY=$$($(MISE) scripts/bootstrap-key.sh get); \
	if [ -n "$$KEY" ]; then echo "AES_BOOTSTRAP_API_KEY=$$KEY"; \
	else echo "chave de bootstrap indisponível: rode make reissue-key"; fi

reissue-key:
	@PGPW=$$($(MISE) kubectl -n aes get secret $(ENV_SECRET) -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d); \
	PGUSER=$$($(MISE) kubectl -n aes get secret $(ENV_SECRET) -o jsonpath='{.data.POSTGRES_USER}' | base64 -d); \
	PGDB=$$($(MISE) kubectl -n aes get secret $(ENV_SECRET) -o jsonpath='{.data.POSTGRES_DB}' | base64 -d); \
	$(MISE) kubectl -n aes exec postgres-0 -- env PGPASSWORD="$$PGPW" \
		psql -v ON_ERROR_STOP=1 -U "$$PGUSER" -d "$$PGDB" -c "DELETE FROM api_keys WHERE name = 'bootstrap';"
	$(MISE) kubectl -n aes delete secret aes-api-bootstrap-key --ignore-not-found
	$(MAKE) deploy
	$(MAKE) creds

smoke:
	$(MISE) scripts/smoke.sh

TAG ?= dev
IMAGE ?= aes-api
ENV_SECRET ?= aes-api-env
CODE_VERSION ?= $(shell IMAGE=$(IMAGE) TAG=$(TAG) scripts/code-version.sh 2>/dev/null)

.PHONY: up build kind-load deploy

up: infra deploy creds

build:
	docker build -f backend/Dockerfile -t $(IMAGE):$(TAG) .

kind-load:
	$(MISE) kind load docker-image $(IMAGE):$(TAG) --name $(CLUSTER)

deploy: build kind-load
	@test -n "$(CODE_VERSION)" || { echo "imagem $(IMAGE):$(TAG) não encontrada; rode make build"; exit 1; }
	$(MISE) helm upgrade --install aes-api charts/aes-api \
		--namespace aes \
		--set image.repository=$(IMAGE) \
		--set image.tag=$(TAG) \
		--set codeVersion=$(CODE_VERSION) \
		--wait --timeout 10m
	$(MISE) kubectl -n aes rollout status deployment/aes-api-api --timeout=5m
	$(MISE) kubectl -n aes rollout status deployment/aes-api-worker --timeout=5m
	$(MISE) scripts/bootstrap-key.sh stash
