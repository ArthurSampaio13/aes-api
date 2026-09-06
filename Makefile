export KUBECONFIG ?= $(HOME)/.kube/kind-aes-local.yaml

CLUSTER ?= aes-local
MISE := mise exec --

.PHONY: setup infra down status grafana creds smoke
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
	@$(MISE) kubectl -n aes logs job/aes-api-seed 2>/dev/null | grep -E '^AES_(BOOTSTRAP_API_KEY|RUBRIC_ID|PROMPT_TEMPLATE_ID)=' \
		|| echo "credenciais indisponíveis: rode make deploy"

smoke:
	$(MISE) scripts/smoke.sh

TAG ?= dev
IMAGE ?= aes-api
CODE_VERSION ?= $(shell git rev-parse --short HEAD)

.PHONY: up build kind-load deploy

up: infra build kind-load deploy creds

build:
	docker build -f backend/Dockerfile -t $(IMAGE):$(TAG) .

kind-load:
	$(MISE) kind load docker-image $(IMAGE):$(TAG) --name $(CLUSTER)

deploy:
	$(MISE) helm upgrade --install aes-api charts/aes-api \
		--namespace aes \
		--set image.repository=$(IMAGE) \
		--set image.tag=$(TAG) \
		--set codeVersion=$(CODE_VERSION) \
		--wait --timeout 10m
