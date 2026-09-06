resource "kind_cluster" "this" {
  name           = var.cluster_name
  node_image     = var.node_image
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"

      # O issuer e assado em cada token de service account, entao precisa estar
      # aqui antes do cluster subir. api-audiences precisa listar o proprio
      # issuer (uso interno) e sts.amazonaws.com, senao o TokenRequest do volume
      # projetado e recusado.
      kubeadm_config_patches = [
        <<-EOT
        kind: ClusterConfiguration
        apiServer:
          extraArgs:
            service-account-issuer: ${var.service_account_issuer}
            api-audiences: ${var.service_account_issuer},sts.amazonaws.com
        EOT
      ]

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
