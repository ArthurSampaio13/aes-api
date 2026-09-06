output "cluster_name" {
  description = "kind cluster name"
  value       = kind_cluster.this.name
}

output "kubeconfig_path" {
  description = "Path to the generated kubeconfig"
  value       = local_sensitive_file.kubeconfig.filename
}

output "cluster_id" {
  value = kind_cluster.this.id
}
