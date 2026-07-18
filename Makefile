.PHONY: cluster-up cluster-down cluster-status

cluster-up:
	kind create cluster --config deploy/kind/cluster.yaml --name aes-local

cluster-down:
	kind delete cluster --name aes-local

cluster-status:
	kubectl --context kind-aes-local get pods -A
