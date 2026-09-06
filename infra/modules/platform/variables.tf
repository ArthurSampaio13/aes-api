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

variable "openrouter_api_key" {
  description = "API key for the openrouter LLM gateway; leave empty to leave the provider unconfigured"
  type        = string
  sensitive   = true
  default     = ""
}

variable "groq_api_key" {
  description = "API key for the groq LLM gateway; leave empty to leave the provider unconfigured"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cerebras_api_key" {
  description = "API key for the cerebras LLM gateway; leave empty to leave the provider unconfigured"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_api_key" {
  description = "API key for the github LLM gateway; leave empty to leave the provider unconfigured"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_api_key" {
  description = "API key for the gemini LLM gateway; leave empty to leave the provider unconfigured"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_role_arn" {
  description = "Role assumed by the API and worker through their projected service account token"
  type        = string
}

variable "aws_region" {
  type = string
}

variable "ocr_provider" {
  description = "mock keeps everything offline; textract calls real AWS"
  type        = string
}

variable "bedrock_model_id" {
  description = "Bedrock inference profile used by the bedrock correction provider"
  type        = string
}

variable "openrouter_model" {
  description = "OpenRouter model id; free tiers come and go, so re-check before relying on one"
  type        = string
}

variable "vision_model_id" {
  description = "Multimodal inference profile used to transcribe handwriting"
  type        = string
}

variable "localstack_image" {
  description = "Pro image; the community one ignores LOCALSTACK_AUTH_TOKEN and the web UI refuses to attach to it"
  type        = string
}
