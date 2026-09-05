variable "kubeconfig_path" {
  description = "Path to the cluster kubeconfig"
  type        = string
}

variable "app_namespace" {
  description = "Namespace holding the AES application and its backing services"
  type        = string
  default     = "aes"
}

variable "monitoring_namespace" {
  description = "Namespace holding Prometheus and Grafana"
  type        = string
  default     = "monitoring"
}

variable "postgres_db" {
  description = "Application database name"
  type        = string
  default     = "postgres"
}

variable "postgres_app_user" {
  description = "Application database role; must be NOSUPERUSER NOBYPASSRLS for RLS to hold"
  type        = string
  default     = "aes_app"
}

variable "postgres_storage" {
  description = "PVC size for the Postgres data directory"
  type        = string
  default     = "2Gi"
}
