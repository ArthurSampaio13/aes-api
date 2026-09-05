output "kubeconfig_path" {
  description = "Path to the cluster kubeconfig"
  value       = module.kind_cluster.kubeconfig_path
}

output "grafana_password" {
  description = "Grafana admin password"
  value       = module.platform.grafana_password
  sensitive   = true
}

output "api_url" {
  description = "Base URL of the API on the host"
  value       = "http://localhost:${var.api_host_port}"
}

output "grafana_url" {
  description = "Grafana URL on the host"
  value       = "http://localhost:${var.grafana_host_port}"
}
