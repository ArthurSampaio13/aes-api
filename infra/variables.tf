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

variable "localstack_auth_token" {
  description = "LocalStack auth token, from TF_VAR_localstack_auth_token"
  type        = string
  sensitive   = true
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

variable "aws_region" {
  description = "Region used by the LocalStack-backed S3 and SQS clients"
  type        = string
  default     = "us-east-1"
}

variable "ocr_provider" {
  description = "mock keeps the stack offline; vision sends the image to an OpenRouter model"
  type        = string
  default     = "mock"
}

variable "openrouter_model" {
  description = "OpenRouter model id; the code default was removed upstream"
  type        = string
  default     = "nvidia/nemotron-3.5-lightning:free"
}

variable "vision_model" {
  description = "OpenRouter model used to transcribe handwriting"
  type        = string
  default     = "deepseek/deepseek-v4.1-flash"
}

variable "localstack_image" {
  description = "The license pins a minimum version: an image older than it fails activation and the container exits 55"
  type        = string
  default     = "localstack/localstack-pro:2026.8.1"
}
