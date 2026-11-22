# infra/aws

CDK (AWS Cloud Development Kit, Python) app that provisions the AWS Batch infrastructure the
`aws` profile in `nextflow.config` expects: an S3 (Simple Storage Service) bucket for the work
dir and results, a security group in the account's default VPC (virtual private cloud), and
three Batch job queues:

- `histostate-gpu-spot` and `histostate-gpu-ondemand`: single-GPU instances (`g4dn.xlarge`,
  `g5.xlarge`) on the ECS (Elastic Container Service) GPU-optimized AMI (Amazon Machine Image),
  which ships the NVIDIA driver. Used by `-profile aws,gpu`.
- `histostate-cpu-spot`: 8 vCPU instances (`c6i.2xlarge`, `c7i.2xlarge`, `m6i.2xlarge`) on the
  standard ECS AMI, for training without a GPU. Used by `-profile aws,cpu`.

The GPU queues use the ECS GPU AMI with an 8 vCPU (virtual CPU) ceiling, the CPU queue is
smaller, instances get a 100 GB root volume, and the stack uses the account's default VPC rather
than creating a new one.

It is its own uv project so CDK's dependencies stay out of the histostate package.

## Prereqs

- Node.js and the AWS CDK CLI 2.1146.0 or newer (`npm install -g aws-cdk`, or
  `npx aws-cdk@2.1146.0`); older CLIs cannot read what `aws-cdk-lib` 2.274 synthesizes
- AWS credentials for the target account (`aws sso login` or `AWS_PROFILE`)
- The account and region bootstrapped once: `uv run cdk bootstrap aws://<account-id>/<region>`
- EC2 (Elastic Compute Cloud) quota for G instances. Batch cannot launch a GPU instance while
  "All G and VT Spot Instance Requests" (Spot) or "Running On-Demand G and VT instances"
  (on-demand) is 0. Check with
  `aws service-quotas get-service-quota --service-code ec2 --quota-code L-3819A6DF`
  (on-demand: `L-DB2E81BA`).

## Deploy

```bash
cd infra/aws
uv sync
uv run pytest
uv run cdk deploy
```

Context defaults (override with `cdk deploy -c max_vcpus=32`):

- `max_vcpus` (default `8`): ceiling for each GPU compute environment; keep it at or below
  the G quota (8 for both Spot and on-demand since 2026-10-22, so two 4 vCPU GPU jobs at once)
- `cpu_max_vcpus` (default `64`): ceiling for the CPU compute environment
- `root_volume_gb` (default `100`): root EBS (Elastic Block Store) volume on Batch instances

## Wire it into the repo

Copy the `EnvSnippet` output into the repo root `.env`, then add `HISTOSTATE_IMAGE`. The image
lives in an ECR (Elastic Container Registry) repository named `histostate`, created once
outside this stack:

```bash
aws ecr create-repository --repository-name histostate \
  --image-scanning-configuration scanOnPush=true \
  --tags Key=project,Value=histostate
```

Build and push from the repo root. Batch instances are x86_64, so build for `linux/amd64` even
on Apple Silicon; tag with the git commit so each run records which code it trained.

```bash
set -a; source .env; set +a
REGISTRY=<account-id>.dkr.ecr.$AWS_REGION.amazonaws.com
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY
docker buildx build --platform linux/amd64 -t $REGISTRY/histostate:$(git rev-parse --short HEAD) --push .
```

For a GPU run that can't tolerate Spot reclamation, set
`AWS_BATCH_GPU_QUEUE=histostate-gpu-ondemand`.

## Teardown

```bash
uv run cdk destroy
```

The S3 bucket has `RemovalPolicy.RETAIN`, so it survives `cdk destroy` and has to be deleted
by hand.

## Cost

Idle cost is close to zero: no NAT gateway, and all compute environments have `minvCpus=0`,
so no instances run between jobs. The ongoing cost is S3 storage under `results/` (`work/`
expires after 30 days) and the image in ECR. Compute is billed only while jobs run.
