# The role the deploy workflow assumes through GitHub's OIDC (OpenID Connect) provider, so no AWS
# keys live in GitHub. Only pushes to this repository's main branch may assume it, and it can only
# create and start deployments on this one Amplify branch and read their status.
# The provider itself is account-wide and shared with glia-nav and methyl-flow, so it is only
# looked up here.

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/${local.branch}"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${local.name}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
}

data "aws_iam_policy_document" "deploy" {
  statement {
    sid = "DeployMainBranch"
    actions = [
      "amplify:CreateDeployment",
      "amplify:StartDeployment",
      "amplify:GetJob",
    ]
    # Amplify authorizes CreateDeployment and StartDeployment on .../deployments/* and GetJob on
    # .../jobs/*, all under this one branch.
    resources = [
      aws_amplify_branch.main.arn,
      "${aws_amplify_branch.main.arn}/deployments/*",
      "${aws_amplify_branch.main.arn}/jobs/*",
    ]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "amplify-deploy"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}
