module "kind_cluster" {
  source = "./modules/kind-cluster"

  cluster_name      = var.cluster_name
  kubeconfig_path   = var.kubeconfig_path
  node_image        = var.node_image
  api_host_port     = var.api_host_port
  grafana_host_port = var.grafana_host_port
}
