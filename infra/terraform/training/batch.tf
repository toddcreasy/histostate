# AWS Batch: what the aws profile in nextflow.config submits to. Three queues, each with its own
# compute environment that scales from 0 instances, so nothing runs (or bills) between jobs.
#   histostate-gpu-spot      single-GPU Spot instances (-profile aws,gpu)
#   histostate-gpu-ondemand  the same on-demand, for runs that can't survive a Spot reclaim
#   histostate-cpu-spot      8 vCPU Spot instances, for training without a GPU (-profile aws,cpu)

# One NVIDIA GPU, 4 vCPUs, 16 GB each: T4 (g4dn) and A10G (g5). Exact sizes, not whole families,
# so Batch never picks a multi-GPU instance. Two types give Spot more capacity pools.
# 8 vCPUs, 16 GB each for the CPU queue.
locals {
  gpu_instance_types = ["g4dn.xlarge", "g5.xlarge"]
  cpu_instance_types = ["c6i.2xlarge", "c7i.2xlarge", "m6i.2xlarge"]
  miniconda_dir      = "/home/ec2-user/miniconda"
}

# The ECS-optimized Amazon Linux 2023 AMIs, looked up when you plan. The GPU one ships the NVIDIA
# driver. A new AMI release shows up as a new launch template version in the next plan.
data "aws_ssm_parameter" "ami_gpu" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/gpu/recommended/image_id"
}

data "aws_ssm_parameter" "ami_cpu" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

# Nextflow runs the AWS CLI from the host at aws.batch.cliPath (nextflow.config), so every
# instance installs it with Miniforge (conda-forge only, no Anaconda licensing) at boot. The
# installer is pinned and checked against the SHA-256 GitHub records for the release asset, so
# a new upstream release can't change what runs as root. Batch merges its own ECS bootstrap into
# this, so it must be MIME multipart.
locals {
  miniforge_version = "26.9.4-2"
  miniforge_sha256  = "bbaf16b3897da24c4be50315934ba74848f617b4495982841d6a0a60e0edbbdf"

  user_data = <<-EOT
    Content-Type: multipart/mixed; boundary="==BOUNDARY=="
    MIME-Version: 1.0

    --==BOUNDARY==
    Content-Type: text/x-shellscript; charset="us-ascii"

    #!/bin/bash
    set -euo pipefail
    curl -fsSL https://github.com/conda-forge/miniforge/releases/download/${local.miniforge_version}/Miniforge3-Linux-x86_64.sh -o /tmp/miniconda.sh
    echo "${local.miniforge_sha256}  /tmp/miniconda.sh" | sha256sum --check -
    bash /tmp/miniconda.sh -b -p ${local.miniconda_dir}
    ${local.miniconda_dir}/bin/conda install -y awscli
    rm -f /tmp/miniconda.sh
    chown -R ec2-user:ec2-user ${local.miniconda_dir}

    --==BOUNDARY==--
  EOT

  launch_templates = {
    gpu = data.aws_ssm_parameter.ami_gpu.insecure_value
    cpu = data.aws_ssm_parameter.ami_cpu.insecure_value
  }
}

resource "aws_launch_template" "batch" {
  for_each = local.launch_templates

  name      = "${local.name}-batch-${each.key}"
  image_id  = each.value
  user_data = base64encode(local.user_data)

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = var.root_volume_gb
      volume_type = "gp3"
      encrypted   = true
    }
  }

  # IMDSv2 only (session tokens). Hop limit 2 so the AWS CLI inside a job's container can still
  # reach the metadata service for the instance role's credentials.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  # The provider's default tags don't reach what Batch launches. The compute environment's tags
  # cover the instances; this covers their root volumes, so both count toward the budget.
  tag_specifications {
    resource_type = "volume"
    tags = {
      project = local.name
    }
  }
}

locals {
  compute_environments = {
    gpu-spot = {
      type       = "SPOT"
      allocation = "SPOT_PRICE_CAPACITY_OPTIMIZED"
      template   = "gpu"
      instances  = local.gpu_instance_types
      max_vcpus  = var.gpu_max_vcpus
    }
    gpu-ondemand = {
      type       = "EC2"
      allocation = "BEST_FIT_PROGRESSIVE"
      template   = "gpu"
      instances  = local.gpu_instance_types
      max_vcpus  = var.gpu_max_vcpus
    }
    cpu-spot = {
      type       = "SPOT"
      allocation = "SPOT_PRICE_CAPACITY_OPTIMIZED"
      template   = "cpu"
      instances  = local.cpu_instance_types
      max_vcpus  = var.cpu_max_vcpus
    }
  }
}

resource "aws_batch_compute_environment" "this" {
  for_each = local.compute_environments

  name = "${local.name}-${each.key}"
  type = "MANAGED"

  compute_resources {
    type                = each.value.type
    allocation_strategy = each.value.allocation
    instance_type       = each.value.instances
    min_vcpus           = 0
    max_vcpus           = each.value.max_vcpus
    subnets             = data.aws_subnets.default.ids
    security_group_ids  = [aws_security_group.compute.id]
    instance_role       = aws_iam_instance_profile.instance.arn

    # Track the newest template version, so a change (a new AMI, a bigger root volume) reaches
    # instances Batch launches after the apply.
    launch_template {
      launch_template_id = aws_launch_template.batch[each.value.template].id
      version            = aws_launch_template.batch[each.value.template].latest_version
    }

    tags = {
      project = local.name
      Name    = "${local.name}-${each.key}"
    }
  }

  update_policy {
    job_execution_timeout_minutes = 30
    terminate_jobs_on_update      = false
  }
}

resource "aws_batch_job_queue" "this" {
  for_each = local.compute_environments

  name     = "${local.name}-${each.key}"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.this[each.key].arn
  }
}
