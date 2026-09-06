resource "random_password" "app_secret_key" {
  length  = 48
  special = false
}

resource "kubernetes_secret" "app_env" {
  metadata {
    name      = "aes-api-env"
    namespace = kubernetes_namespace.app.metadata[0].name
  }

  data = merge({
    POSTGRES_SERVER   = kubernetes_service.postgres.metadata[0].name
    POSTGRES_PORT     = "5432"
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_app_user
    POSTGRES_PASSWORD = random_password.postgres_app.result

    AES_STORAGE_ENDPOINT_URL = local.localstack_endpoint
    AES_STORAGE_BUCKET       = var.storage_bucket
    AES_STORAGE_ACCESS_KEY   = "test"
    AES_STORAGE_SECRET_KEY   = "test"
    AWS_DEFAULT_REGION       = "us-east-1"

    TASKIQ_BROKER_TYPE      = "sqs"
    TASKIQ_SQS_ENDPOINT_URL = local.localstack_endpoint
    TASKIQ_SQS_QUEUE_URL    = local.sqs_queue_url
    TASKIQ_SQS_REGION       = "us-east-1"
    TASKIQ_SQS_ACCESS_KEY   = "test"
    TASKIQ_SQS_SECRET_KEY   = "test"

    CACHE_BACKEND        = "memory"
    SESSION_BACKEND      = "memory"
    RATE_LIMITER_ENABLED = "false"
    AES_OCR_PROVIDER     = var.ocr_provider

    # O boto3 monta credenciais sozinho a partir destas tres: troca o token do
    # service account projetado por credenciais temporarias via
    # AssumeRoleWithWebIdentity. Nao ha chave estatica em lugar nenhum.
    AWS_ROLE_ARN                = var.aws_role_arn
    AWS_WEB_IDENTITY_TOKEN_FILE = "/var/run/secrets/aws/token"
    AWS_REGION                  = var.aws_region

    SESSION_SECURE_COOKIES                 = "false"
    PRODUCTION_SECURITY_VALIDATION_ENABLED = "false"

    SECRET_KEY = random_password.app_secret_key.result
  }, local.gateway_api_keys)

  depends_on = [kubernetes_stateful_set.postgres, kubernetes_deployment.localstack]
}

locals {
  gateway_api_keys = {
    for name, key in {
      OPENROUTER_API_KEY = var.openrouter_api_key
      GROQ_API_KEY       = var.groq_api_key
      CEREBRAS_API_KEY   = var.cerebras_api_key
      GITHUB_API_KEY     = var.github_api_key
      GEMINI_API_KEY     = var.gemini_api_key
    } : name => key if key != ""
  }
}
