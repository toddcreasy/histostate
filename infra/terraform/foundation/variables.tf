variable "account_id" {
  description = "The AWS account this stack may touch; Terraform refuses any other (a stale AWS_PROFILE, say)."
  type        = string
}

variable "budget_email" {
  description = "Address that gets the budget alerts."
  type        = string
}

variable "budget_limit_usd" {
  description = "Monthly spend limit for resources tagged project=histostate."
  type        = number
}
