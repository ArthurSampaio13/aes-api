variable "cluster_name" {
  description = "kind cluster name"
  type        = string
}

variable "kubeconfig_path" {
  description = "Where to write the kubeconfig"
  type        = string
}

variable "node_image" {
  description = "kindest/node image with digest, matching the kubectl version in mise.toml"
  type        = string
}

variable "api_host_port" {
  description = "Host port published for the API NodePort"
  type        = number
}

variable "grafana_host_port" {
  description = "Host port published for the Grafana NodePort"
  type        = number
}

variable "service_account_issuer" {
  description = "Public HTTPS URL serving the OIDC discovery document for this cluster"
  type        = string
}
