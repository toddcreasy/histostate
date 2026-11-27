# The website on Amplify Hosting, as glia-nav does it. The app has no repository attached: the
# deploy workflow (.github/workflows/deploy.yml) builds frontend/ and uploads the static export
# through the Amplify deployment API with the OIDC role in github_oidc.tf. That way no long-lived
# GitHub token is stored in AWS.

resource "aws_amplify_app" "site" {
  name        = local.name
  description = "histostate website: the CNN running in the visitor's browser"
  platform    = "WEB"

  # Paths with no file get the static export's 404 page in place. "404-200" is the console's
  # "404 (Rewrite)"; plain "404" ("404 (Redirect)") answered with a 302 to /404.html instead.
  custom_rule {
    source = "/<*>"
    target = "/404.html"
    status = "404-200"
  }

  # Security headers on every response (local.custom_headers). Amplify takes them under a
  # customHeaders key but reads them back as a bare list, so Terraform would see a change on every
  # plan. It sets them at creation and then ignores the read-back; terraform_data.custom_headers
  # below pushes any later change.
  custom_headers = local.custom_headers
  lifecycle {
    ignore_changes = [custom_headers]
  }
}

locals {
  # YAML (JSON is valid YAML) under a customHeaders key; a bare list is rejected ("top level must
  # be key value pairs").
  custom_headers = jsonencode({
    customHeaders = [{
      pattern = "**/*"
      headers = [
        { key = "Strict-Transport-Security", value = "max-age=31536000; includeSubDomains" },
        { key = "X-Content-Type-Options", value = "nosniff" },
        { key = "X-Frame-Options", value = "DENY" },
        { key = "Referrer-Policy", value = "strict-origin-when-cross-origin" },
        { key = "Content-Security-Policy", value = local.content_security_policy },
      ]
    }]
  })
}

# Drift: the app ignores its custom_headers read-back, so a header edited or removed in the console
# would never show in a plan. This compares the live headers with local.custom_headers, both as
# the same JSON list, and warns on every plan and apply where they differ.
check "custom_headers_match_live" {
  assert {
    # Before Amplify reads them back (a new app, or a mocked test) the value is still the object
    # form written here; after, it's the bare list. Either one, matching the code, is in sync.
    condition = contains([
      jsonencode(jsondecode(local.custom_headers)),
      jsonencode(jsondecode(local.custom_headers).customHeaders),
    ], jsonencode(jsondecode(aws_amplify_app.site.custom_headers)))
    error_message = "The site's live security headers differ from local.custom_headers in amplify.tf. Restore them with: terraform apply -replace=terraform_data.custom_headers"
  }
}

# Replaced whenever local.custom_headers changes, which pushes the new headers to the app.
resource "terraform_data" "custom_headers" {
  triggers_replace = local.custom_headers

  provisioner "local-exec" {
    command = "aws amplify update-app --region us-east-1 --app-id \"$APP_ID\" --custom-headers \"$HEADERS\" --query app.appId --output text"
    environment = {
      APP_ID  = aws_amplify_app.site.id
      HEADERS = local.custom_headers
    }
  }
}

# Only this site's own files. The static export has inline scripts (page data, and the theme
# script that runs before first paint), so script-src needs 'unsafe-inline'; ONNX Runtime compiles
# WebAssembly, which needs 'wasm-unsafe-eval'. connect-src allows https: so an image dragged in
# from another site still loads when that site permits it (CORS), as it did before this policy,
# and data: for dropped data URLs. Tested in Chrome against a local build before it went live:
# classify, drop, upload, no violations.
locals {
  content_security_policy = join("; ", [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self' https: data:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ])
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
