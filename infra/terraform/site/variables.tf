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
  description = "owner/name of the repository whose main branch may deploy the site."
  type        = string
  default     = "toddcreasy/histostate"
}
