export KUBECONFIG ?= $(HOME)/.kube/kind-aes-local.yaml

CLUSTER ?= aes-local

.PHONY: setup infra down status grafana creds smoke
.NOTPARALLEL:

setup:
	mise install
	pre-commit install

infra:
	tofu -chdir=infra init -upgrade
	tofu -chdir=infra apply -auto-approve

down:
	tofu -chdir=infra destroy -auto-approve
	-kind delete cluster --name $(CLUSTER)
	rm -rf infra/.state

status:
	kubectl get pods -A

grafana:
	@echo "URL:  $$(tofu -chdir=infra output -raw grafana_url)"
	@echo "user: admin"
	@echo "pass: $$(tofu -chdir=infra output -raw grafana_password)"

creds:
	@echo "API:   $$(tofu -chdir=infra output -raw api_url)"
	@echo "Docs:  $$(tofu -chdir=infra output -raw api_url)/docs"
	@kubectl -n aes logs job/aes-api-seed 2>/dev/null | grep -E '^AES_(BOOTSTRAP_API_KEY|RUBRIC_ID|PROMPT_TEMPLATE_ID)=' \
		|| echo "credenciais indisponíveis: rode make deploy"

smoke:
	scripts/smoke.sh

TAG ?= dev
IMAGE ?= aes-api
CODE_VERSION ?= $(shell git rev-parse --short HEAD)

.PHONY: up build kind-load deploy

up: infra build kind-load deploy creds

build:
	docker build -f backend/Dockerfile -t $(IMAGE):$(TAG) .

kind-load:
	kind load docker-image $(IMAGE):$(TAG) --name $(CLUSTER)

deploy:
	helm upgrade --install aes-api charts/aes-api \
		--namespace aes \
		--set image.repository=$(IMAGE) \
		--set image.tag=$(TAG) \
		--set codeVersion=$(CODE_VERSION) \
		--wait --timeout 10m
