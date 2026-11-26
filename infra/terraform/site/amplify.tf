# The website on Amplify Hosting, as glia-nav does it. The app has no repository attached: the
# deploy workflow (.github/workflows/deploy.yml) builds frontend/ and uploads the static export
# through the Amplify deployment API with the OIDC role in github_oidc.tf. That way no long-lived
# GitHub token is stored in AWS.

resource "aws_amplify_app" "site" {
  name        = local.name
  description = "histostate website: the CNN running in the visitor's browser"
  platform    = "WEB"

  # Paths with no file get the static export's 404 page, with a 404 status.
  custom_rule {
    source = "/<*>"
    target = "/404.html"
    status = "404"
  }

  # Security headers on every response. No Content-Security-Policy yet: the static export uses
  # inline scripts and ONNX Runtime needs 'wasm-unsafe-eval', so one needs testing on its own.
  # Written as the JSON list Amplify stores them as; YAML is accepted but reads back different,
  # so every plan would show a change.
  custom_headers = jsonencode([{
    pattern = "**/*"
    headers = [
      { key = "Strict-Transport-Security", value = "max-age=31536000; includeSubDomains" },
      { key = "X-Content-Type-Options", value = "nosniff" },
      { key = "X-Frame-Options", value = "DENY" },
      { key = "Referrer-Policy", value = "strict-origin-when-cross-origin" },
    ]
  }])
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.site.id
  branch_name = local.branch
  stage       = "PRODUCTION"
}

# The zone is in this account, so Amplify writes its certificate validation and alias records
# into it on its own. Terraform waits until the certificate is issued.
resource "aws_amplify_domain_association" "site" {
  app_id                 = aws_amplify_app.site.id
  domain_name            = var.domain_name
  enable_auto_sub_domain = false

  sub_domain {
    branch_name = aws_amplify_branch.main.branch_name
    prefix      = ""
  }
}
