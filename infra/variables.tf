variable "cluster_name" {
  description = "kind cluster name"
  type        = string
  default     = "aes-local"
}

variable "kubeconfig_path" {
  description = "Where to write the kubeconfig"
  type        = string
  default     = "~/.kube/kind-aes-local.yaml"
}

variable "node_image" {
  description = "kindest/node image with digest"
  type        = string
}

variable "api_host_port" {
  description = "Host port published for the API"
  type        = number
  default     = 8000
}

variable "grafana_host_port" {
  description = "Host port published for Grafana"
  type        = number
  default     = 3000
}
