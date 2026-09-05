output "kubeconfig_path" {
  description = "Path to the cluster kubeconfig"
  value       = module.kind_cluster.kubeconfig_path
}
