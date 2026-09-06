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
  openrouter_api_key    = var.openrouter_api_key
  groq_api_key          = var.groq_api_key
  cerebras_api_key      = var.cerebras_api_key
  github_api_key        = var.github_api_key
  gemini_api_key        = var.gemini_api_key
}
