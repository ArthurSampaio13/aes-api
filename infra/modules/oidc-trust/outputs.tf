output "role_arn" {
  description = "Role the API and worker assume through their projected service account token"
  value       = aws_iam_role.workload.arn
}
