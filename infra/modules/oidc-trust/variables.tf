variable "issuer_url" {
  description = "OIDC issuer URL, matching the kube-apiserver's service-account-issuer"
  type        = string
}

variable "bucket" {
  description = "Bucket serving the discovery document"
  type        = string
}

variable "kubeconfig_path" {
  type = string
}

variable "cluster_id" {
  description = "Ties the JWKS read to the cluster resource, so it is deferred until the cluster exists"
  type        = string
}

variable "namespace" {
  type = string
}

variable "service_account_name" {
  type = string
}
