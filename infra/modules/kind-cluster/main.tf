resource "kind_cluster" "this" {
  name           = var.cluster_name
  node_image     = var.node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      extra_port_mappings {
        container_port = 30080
        host_port      = var.api_host_port
        listen_address = "127.0.0.1"
      }

      extra_port_mappings {
        container_port = 30300
        host_port      = var.grafana_host_port
        listen_address = "127.0.0.1"
      }
    }
  }
}

resource "local_sensitive_file" "kubeconfig" {
  content         = kind_cluster.this.kubeconfig
  filename        = pathexpand(var.kubeconfig_path)
  file_permission = "0600"
}
