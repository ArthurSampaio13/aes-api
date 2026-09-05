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

variable "localstack_auth_token" {
  description = "LocalStack auth token; required on every tier since the Community Edition was retired in March 2026"
  type        = string
  sensitive   = true
}

variable "storage_bucket" {
  description = "S3 bucket holding submissions, OCR transcriptions and raw provider responses"
  type        = string
  default     = "aes-submissions"
}

variable "sqs_queue_name" {
  description = "SQS queue backing the Taskiq broker"
  type        = string
  default     = "default"
}

variable "kube_prometheus_stack_version" {
  description = "Pinned kube-prometheus-stack chart version"
  type        = string
  default     = "88.6.1"
}
