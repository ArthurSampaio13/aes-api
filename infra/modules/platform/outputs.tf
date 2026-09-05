output "grafana_password" {
  description = "Grafana admin password"
  value       = random_password.grafana.result
  sensitive   = true
}

output "app_namespace" {
  description = "Namespace holding the AES application"
  value       = kubernetes_namespace.app.metadata[0].name
}
