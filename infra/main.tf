module "kind_cluster" {
  source = "./modules/kind-cluster"

  cluster_name      = var.cluster_name
  kubeconfig_path   = var.kubeconfig_path
  node_image        = var.node_image
  api_host_port     = var.api_host_port
  grafana_host_port = var.grafana_host_port
}

module "platform" {
  source = "./modules/platform"

  kubeconfig_path       = module.kind_cluster.kubeconfig_path
  localstack_auth_token = var.localstack_auth_token
}
