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

variable "aws_profile" {
  description = "Local AWS profile used to provision the OIDC bucket and IAM role"
  type        = string
  default     = "tcc"
}

variable "aws_region" {
  description = "Textract is not offered in sa-east-1; keep this on a region that has it"
  type        = string
  default     = "us-east-1"
}

variable "ocr_provider" {
  description = "mock keeps the stack offline; textract calls real AWS through the assumed role"
  type        = string
  default     = "textract"
}

variable "bedrock_model_id" {
  description = "Inference profile, not a bare model id: the Claude models on this account are INFERENCE_PROFILE only"
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "openrouter_model" {
  description = "OpenRouter model id; the code default was removed upstream"
  type        = string
  default     = "nvidia/nemotron-3.5-lightning:free"
}
