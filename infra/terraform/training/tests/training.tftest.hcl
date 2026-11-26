# Runs against a mocked AWS provider: no credentials, no real resources.
#   terraform test

mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }
  mock_data "aws_region" {
    defaults = {
      region = "us-east-1"
    }
  }
  mock_data "aws_subnets" {
    defaults = {
      ids = ["subnet-aaaa", "subnet-bbbb"]
    }
  }
  mock_data "aws_ssm_parameter" {
    defaults = {
      insecure_value = "ami-0123456789abcdef0"
    }
  }
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{}"
    }
  }
  # Known during plan, so policy checks can read the bucket ARN.
  mock_resource "aws_s3_bucket" {
    override_during = plan
    defaults = {
      arn = "arn:aws:s3:::histostate-batch-123456789012"
    }
  }
  mock_resource "aws_iam_instance_profile" {
    defaults = {
      arn = "arn:aws:iam::123456789012:instance-profile/histostate-batch-instance"
    }
  }
  mock_resource "aws_batch_compute_environment" {
    defaults = {
      arn = "arn:aws:batch:us-east-1:123456789012:compute-environment/histostate"
    }
  }
}

variables {
  account_id = "123456789012"
}

run "bucket_blocks_all_public_access" {
  command = plan
  assert {
    condition = alltrue([
      aws_s3_bucket_public_access_block.batch.block_public_acls,
      aws_s3_bucket_public_access_block.batch.block_public_policy,
      aws_s3_bucket_public_access_block.batch.ignore_public_acls,
      aws_s3_bucket_public_access_block.batch.restrict_public_buckets,
    ])
    error_message = "The batch bucket must block every kind of public access."
  }
}

run "bucket_refuses_plain_http" {
  command = plan
  assert {
    condition = (
      data.aws_iam_policy_document.batch_tls_only.statement[0].effect == "Deny" &&
      one(data.aws_iam_policy_document.batch_tls_only.statement[0].condition).variable == "aws:SecureTransport"
    )
    error_message = "The batch bucket policy must deny requests that aren't over TLS."
  }
}

run "work_dir_expires_after_30_days" {
  command = plan
  assert {
    condition = anytrue([
      for r in aws_s3_bucket_lifecycle_configuration.batch.rule :
      r.status == "Enabled" && one(r.filter).prefix == "work/" && one(r.expiration).days == 30
    ])
    error_message = "Nextflow's work/ prefix must expire after 30 days."
  }
}

run "ecr_tags_immutable_and_scanned" {
  command = plan
  assert {
    condition = (
      aws_ecr_repository.training.image_tag_mutability == "IMMUTABLE" &&
      aws_ecr_repository.training.image_scanning_configuration[0].scan_on_push
    )
    error_message = "ECR tags must be immutable (a tag is a git commit) and images scanned on push."
  }
}

run "queues_match_nextflow_config" {
  command = plan
  assert {
    condition = (
      toset([for q in aws_batch_job_queue.this : q.name]) ==
      toset(["histostate-gpu-spot", "histostate-gpu-ondemand", "histostate-cpu-spot"])
    )
    error_message = "Queue names must be the ones .env and nextflow.config use."
  }
}

run "compute_scales_to_zero" {
  command = plan
  assert {
    condition = alltrue([
      for ce in aws_batch_compute_environment.this : ce.compute_resources[0].min_vcpus == 0
    ])
    error_message = "Every compute environment must scale to 0 vCPUs, so nothing bills between jobs."
  }
}

run "gpu_instances_have_one_gpu" {
  command = plan
  assert {
    condition = alltrue([
      for k in ["gpu-spot", "gpu-ondemand"] :
      toset(aws_batch_compute_environment.this[k].compute_resources[0].instance_type) ==
      toset(["g4dn.xlarge", "g5.xlarge"])
    ])
    error_message = "GPU environments must list exact single-GPU sizes, never whole families."
  }
}

run "instances_require_imdsv2_and_encrypt_disks" {
  command = plan
  assert {
    condition = alltrue([
      for lt in aws_launch_template.batch :
      lt.metadata_options[0].http_tokens == "required" &&
      lt.metadata_options[0].http_put_response_hop_limit == 2 &&
      lt.block_device_mappings[0].ebs[0].encrypted == "true"
    ])
    error_message = "Launch templates must require IMDSv2 (hop limit 2 for containers) and encrypt the root volume."
  }
}

run "instance_role_reaches_only_this_bucket" {
  command = plan
  assert {
    condition = alltrue(flatten([
      for s in data.aws_iam_policy_document.instance_bucket.statement : [
        for r in s.resources : startswith(r, "arn:aws:s3:::histostate-batch-123456789012")
      ]
    ]))
    error_message = "The instance role's S3 access must be limited to the batch bucket."
  }
}
