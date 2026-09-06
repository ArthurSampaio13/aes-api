module "oidc_issuer" {
  source = "./modules/oidc-issuer"

  region = var.aws_region
}

module "kind_cluster" {
  source = "./modules/kind-cluster"

  service_account_issuer = module.oidc_issuer.issuer_url
  cluster_name           = var.cluster_name
  kubeconfig_path        = var.kubeconfig_path
  node_image             = var.node_image
  api_host_port          = var.api_host_port
  grafana_host_port      = var.grafana_host_port
}

module "oidc_trust" {
  source = "./modules/oidc-trust"

  issuer_url           = module.oidc_issuer.issuer_url
  bucket               = module.oidc_issuer.bucket
  kubeconfig_path      = module.kind_cluster.kubeconfig_path
  cluster_id           = module.kind_cluster.cluster_id
  namespace            = "aes"
  service_account_name = "aes-api"
}

module "platform" {
  source = "./modules/platform"

  aws_role_arn          = module.oidc_trust.role_arn
  aws_region            = var.aws_region
  ocr_provider          = var.ocr_provider
  kubeconfig_path       = module.kind_cluster.kubeconfig_path
  localstack_auth_token = var.localstack_auth_token
  openrouter_api_key    = var.openrouter_api_key
  groq_api_key          = var.groq_api_key
  cerebras_api_key      = var.cerebras_api_key
  github_api_key        = var.github_api_key
  gemini_api_key        = var.gemini_api_key
}
