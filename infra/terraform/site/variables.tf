variable "account_id" {
  description = "The AWS account this stack may touch; Terraform refuses any other (a stale AWS_PROFILE, say)."
  type        = string
}

variable "domain_name" {
  description = "The site's own name. Its Route 53 zone is made in project-template's ops/dns and delegated from the parent domain."
  type        = string
  default     = "histostate.pilotbio.io"
}

variable "github_repository" {
  description = "The repository whose main branch may deploy the site, as its OIDC token names it. The repo uses GitHub's immutable subjects (gh api repos/OWNER/REPO/actions/oidc/customization/sub), so owner and repository carry their numeric IDs and a renamed or recreated repository can't match."
  type        = string
  default     = "toddcreasy@5910177/histostate@1393796442"
}
