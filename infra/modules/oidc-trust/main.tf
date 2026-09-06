data "external" "jwks" {
  program = ["bash", "${path.module}/files/fetch-jwks.sh"]

  query = {
    kubeconfig = var.kubeconfig_path
    cluster    = var.cluster_id
  }
}

resource "aws_s3_object" "jwks" {
  bucket       = var.bucket
  key          = "keys.json"
  content      = data.external.jwks.result.jwks
  content_type = "application/json"
}

data "tls_certificate" "issuer" {
  url = var.issuer_url
}

resource "aws_iam_openid_connect_provider" "this" {
  url             = var.issuer_url
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.issuer.certificates[length(data.tls_certificate.issuer.certificates) - 1].sha1_fingerprint]
}

data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.this.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.issuer_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "textract" {
  name               = "aes-api-textract"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "textract" {
  statement {
    effect    = "Allow"
    actions   = ["textract:DetectDocumentText"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "textract" {
  name   = "textract-detect-only"
  role   = aws_iam_role.textract.id
  policy = data.aws_iam_policy_document.textract.json
}
