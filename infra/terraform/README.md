# Terraform

Every AWS resource for histostate, built with Terraform the way `ehr-rwe-eln` does it. Each stack
has its own state file in one S3 bucket, `histostate-tfstate-<account ID>`.

| Stack | What it holds | State key |
|---|---|---|
| `bootstrap/` | The state bucket itself (versioned, encrypted, private, TLS only, old versions expire after 90 days) | `bootstrap/terraform.tfstate` |
| `foundation/` | The monthly budget on resources tagged `project=histostate`, with email alerts at 50% and 80% of actual spend and 100% of forecast | `foundation/terraform.tfstate` |
| `training/` | What `nextflow run main.nf -profile aws,...` submits to: the S3 bucket for Nextflow's `work/` (expires after 30 days) and `results/`, the ECR repository for the training image (immutable tags, 10 newest kept), and AWS Batch: three job queues (`histostate-gpu-spot`, `histostate-gpu-ondemand`, `histostate-cpu-spot`), each on a compute environment that scales to 0, in the account's default VPC. `terraform output -raw env` prints the `.env` lines | `training/terraform.tfstate` |

Every resource is tagged `project=histostate` and `managed-by=terraform`. The budget counts only
the `project` tag. Account-wide settings (the CloudTrail trail, Bedrock invocation logging) are
managed in `ehr-rwe-eln`, not here.

## Run a stack

The state bucket's name holds the account ID, so it goes in at `init`, not in the repo. Each stack
takes `account_id` in `terraform.tfvars` (gitignored; copy the `.example`), and its provider sets
`allowed_account_ids`, so a plan against any other account fails before it reads anything.

```sh
cd infra/terraform/foundation
cp terraform.tfvars.example terraform.tfvars      # first time; fill in
terraform init -backend-config="bucket=histostate-tfstate-$(aws sts get-caller-identity --query Account --output text)"
terraform plan -out=foundation.tfplan
terraform apply foundation.tfplan                  # only after the plan is reviewed
```

Applies run from a laptop. CI's `terraform` job runs `fmt`, `validate`, TFLint, and Trivy on every
pull request, with no AWS credentials. A Trivy finding that is a deliberate choice gets a
`# trivy:ignore:<ID> <reason>` comment above the resource.

## Train on AWS

Needs the three stacks applied, AWS credentials (`aws sso login`, single sign-on), Docker, and
Nextflow >= 26.04 with Java 17 or newer.

GPU jobs also need EC2 (Elastic Compute Cloud) quota for G instances: Batch cannot launch one while
"All G and VT Spot Instance Requests" (Spot) or "Running On-Demand G and VT instances" (on-demand)
is 0. Check with
`aws service-quotas get-service-quota --service-code ec2 --quota-code L-3819A6DF` (on-demand:
`L-DB2E81BA`). Both were 8 vCPUs (virtual CPUs) on 2026-10-22, so `gpu_max_vcpus` is 8: two 4 vCPU
GPU jobs at once.

Write `.env` (gitignored) from the stack's outputs, then add the image. `output -raw` ends without
a newline, so `printf` adds one before the second line is appended:

```sh
printf '%s\n' "$(terraform -chdir=infra/terraform/training output -raw env)" > .env
echo "HISTOSTATE_IMAGE=$(terraform -chdir=infra/terraform/training output -raw ecr_repository_url):$(git rev-parse --short HEAD)" >> .env
```

Build and push from the repo root. Batch instances are x86_64, so build for `linux/amd64` even on
Apple Silicon. The tag is the git commit, so each run records which code it trained; tags are
immutable, so a commit is pushed once.

```sh
set -a; source .env; set +a
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${HISTOSTATE_IMAGE%%/*}
docker buildx build --platform linux/amd64 -t $HISTOSTATE_IMAGE --push .
nextflow run main.nf -profile aws,cpu --epochs 1 --size 28 --outdir s3://<bucket>/results/smoke   # a few minutes, a few cents
```

For a GPU run that can't survive a Spot reclaim, set `AWS_BATCH_GPU_QUEUE=histostate-gpu-ondemand`.

Idle cost is close to zero: no NAT (network address translation) gateway, and every compute
environment scales to 0 vCPUs. What
bills between runs is S3 storage under `results/` (`work/` expires after 30 days) and the images in
ECR (10 newest kept).

## How the state bucket was made

The bucket can't hold its own state before it exists. `bootstrap/` was applied once with local
state, using a temporary `backend_override.tf` containing `terraform { backend "local" {} }`.
Then the override was deleted and
`terraform init -migrate-state -backend-config="bucket=histostate-tfstate-<account ID>"` moved the
state into the bucket, and the local state file was deleted. Never apply bootstrap without the
backend config again: it would try to create the bucket a second time.
