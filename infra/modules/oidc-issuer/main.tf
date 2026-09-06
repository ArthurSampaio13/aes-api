# A AWS precisa buscar o documento de descoberta OIDC e o JWKS do cluster por
# HTTPS publico. Um cluster kind roda no notebook e nao e alcancavel, entao o
# bucket faz esse papel: o kube-apiserver assina tokens com este bucket como
# `issuer`, e a AWS valida a assinatura contra o keys.json publicado aqui.
#
# O nome precisa ser conhecido antes do cluster subir, porque o issuer e gravado
# no kubeadm e assado em cada token emitido.

# O nome precisa ser deterministico, nao aleatorio: o issuer tem que ser
# conhecido em tempo de plan, senao o provider do kind nao gera diff no
# kubeadm_config_patches e o cluster sobe silenciosamente com o emissor antigo.
# Derivar do account id garante isso e mantem o bucket estavel entre um
# make down/up.
#
# O hash existe so para o id da conta nao aparecer em claro no nome de um bucket
# publico, que vaza em print, log e saida de plan. Nao trate como segredo: sao
# 12 digitos, entao quem tiver o nome do bucket reverte por forca bruta em
# segundos. Para resistir a isso seria preciso um salt fora do repositorio.
data "aws_caller_identity" "current" {}

locals {
  bucket_name = "aes-api-oidc-${substr(sha256(data.aws_caller_identity.current.account_id), 0, 20)}"
  issuer_url  = "https://${local.bucket_name}.s3.${var.region}.amazonaws.com"
}

resource "aws_s3_bucket" "oidc" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "oidc" {
  bucket = aws_s3_bucket.oidc.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "public_read" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.oidc.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "oidc" {
  bucket     = aws_s3_bucket.oidc.id
  policy     = data.aws_iam_policy_document.public_read.json
  depends_on = [aws_s3_bucket_public_access_block.oidc]
}

resource "aws_s3_object" "discovery" {
  bucket       = aws_s3_bucket.oidc.id
  key          = ".well-known/openid-configuration"
  content_type = "application/json"

  content = jsonencode({
    issuer                                = "${local.issuer_url}"
    jwks_uri                              = "${local.issuer_url}/keys.json"
    authorization_endpoint                = "urn:kubernetes:programmatic_authorization"
    response_types_supported              = ["id_token"]
    subject_types_supported               = ["public"]
    id_token_signing_alg_values_supported = ["RS256"]
    claims_supported                      = ["sub", "iss"]
  })
}
