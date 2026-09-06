output "issuer_url" {
  description = "Issuer the kube-apiserver must stamp into service account tokens"
  value       = local.issuer_url
}

output "bucket" {
  value = aws_s3_bucket.oidc.id
}
