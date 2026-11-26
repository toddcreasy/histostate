# Terraform

Every AWS resource for histostate, built with Terraform the way `ehr-rwe-eln` does it. Each stack
has its own state file in one S3 bucket, `histostate-tfstate-<account ID>`.

| Stack | What it holds | State key |
|---|---|---|
| `bootstrap/` | The state bucket itself (versioned, encrypted, private, TLS only, old versions expire after 90 days) | `bootstrap/terraform.tfstate` |
| `foundation/` | The monthly budget on resources tagged `project=histostate`, with email alerts at 50% and 80% of actual spend and 100% of forecast | `foundation/terraform.tfstate` |

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

## How the state bucket was made

The bucket can't hold its own state before it exists. `bootstrap/` was applied once with local
state, using a temporary `backend_override.tf` containing `terraform { backend "local" {} }`.
Then the override was deleted and
`terraform init -migrate-state -backend-config="bucket=histostate-tfstate-<account ID>"` moved the
state into the bucket, and the local state file was deleted. Never apply bootstrap without the
backend config again: it would try to create the bucket a second time.
