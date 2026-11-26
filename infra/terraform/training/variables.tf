variable "account_id" {
  description = "The AWS account this stack may touch; Terraform refuses any other (a stale AWS_PROFILE, say)."
  type        = string
}

variable "gpu_max_vcpus" {
  description = "Ceiling for each GPU compute environment. Keep it at or below the account's G instance quota (8 since 2026-10-22: two 4 vCPU jobs at once)."
  type        = number
  default     = 8
}

variable "cpu_max_vcpus" {
  description = "Ceiling for the CPU compute environment."
  type        = number
  default     = 64
}

variable "root_volume_gb" {
  description = "Root EBS volume on every Batch instance, in GB. Holds the training image and PathMNIST."
  type        = number
  default     = 100
}
