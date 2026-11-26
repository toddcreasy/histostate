# deploy.yml reads these two from repository variables DEPLOY_ROLE_ARN and AMPLIFY_APP_ID.
output "amplify_app_id" {
  value = aws_amplify_app.site.id
}

output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}

output "site_url" {
  value = "https://${var.domain_name}"
}

output "amplify_url" {
  value = "https://${local.branch}.${aws_amplify_app.site.default_domain}"
}
