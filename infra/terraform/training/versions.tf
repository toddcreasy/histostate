terraform {
  required_version = "~> 1.17"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.73"
    }
  }

  # Partial config: the bucket name holds the account ID, so it comes from
  # `terraform init -backend-config="bucket=..."` and stays out of the repo.
  backend "s3" {
    key          = "training/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      project    = "histostate"
      managed-by = "terraform"
    }
  }
}

data "aws_region" "current" {}

locals {
  name   = "histostate"
  region = data.aws_region.current.region
}
