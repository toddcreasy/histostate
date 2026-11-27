# Runs against a mocked AWS provider: no credentials, no real resources.
#   terraform test

mock_provider "aws" {
  mock_data "aws_iam_openid_connect_provider" {
    defaults = {
      arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    }
  }
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{}"
    }
  }
  # Known during plan, so the deploy policy check can read the branch ARN.
  mock_resource "aws_amplify_branch" {
    override_during = plan
    defaults = {
      arn = "arn:aws:amplify:us-east-1:123456789012:apps/d123/branches/main"
    }
  }
}

variables {
  account_id = "123456789012"
}

run "site_answers_on_its_own_name" {
  command = plan
  assert {
    condition = (
      aws_amplify_domain_association.site.domain_name == "histostate.pilotbio.io" &&
      one(aws_amplify_domain_association.site.sub_domain).prefix == "" &&
      one(aws_amplify_domain_association.site.sub_domain).branch_name == "main"
    )
    error_message = "histostate.pilotbio.io itself (no prefix) must serve the main branch."
  }
}

run "main_is_production" {
  command = plan
  assert {
    condition     = aws_amplify_branch.main.stage == "PRODUCTION"
    error_message = "The main branch must be the production stage."
  }
}

run "responses_force_https" {
  command = plan
  assert {
    condition     = strcontains(aws_amplify_app.site.custom_headers, "Strict-Transport-Security")
    error_message = "Every response must carry Strict-Transport-Security."
  }
}

run "pages_run_only_this_sites_code" {
  command = plan
  assert {
    condition = (
      strcontains(aws_amplify_app.site.custom_headers, "Content-Security-Policy") &&
      strcontains(aws_amplify_app.site.custom_headers, "default-src 'self'") &&
      strcontains(aws_amplify_app.site.custom_headers, "frame-ancestors 'none'")
    )
    error_message = "Every response must carry a Content-Security-Policy limited to this site's own files."
  }
}

run "missing_pages_are_rewritten_not_redirected" {
  command = plan
  assert {
    condition     = one([for r in aws_amplify_app.site.custom_rule : r.status if r.target == "/404.html"]) == "404-200"
    error_message = "The 404 rule must rewrite to /404.html (404-200), not redirect to it."
  }
}

run "only_main_of_this_repo_can_deploy" {
  command = plan
  assert {
    condition = anytrue([
      for c in data.aws_iam_policy_document.deploy_trust.statement[0].condition :
      c.variable == "token.actions.githubusercontent.com:sub" &&
      c.test == "StringEquals" &&
      toset(c.values) == toset(["repo:toddcreasy@5910177/histostate@1393796442:ref:refs/heads/main"])
    ])
    error_message = "The deploy role must trust only pushes to main of toddcreasy/histostate."
  }
}

run "deploy_role_reaches_only_this_branch" {
  command = plan
  assert {
    condition = alltrue([
      for r in data.aws_iam_policy_document.deploy.statement[0].resources :
      startswith(r, "arn:aws:amplify:us-east-1:123456789012:apps/d123/branches/main")
    ])
    error_message = "The deploy role may only deploy to this app's main branch."
  }
}
