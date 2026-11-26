output "bucket" {
  value = aws_s3_bucket.batch.bucket
}

output "ecr_repository_url" {
  value = aws_ecr_repository.training.repository_url
}

output "job_queues" {
  value = { for k, q in aws_batch_job_queue.this : k => q.name }
}

# Paste into the repo root .env (see .env.example), then add HISTOSTATE_IMAGE.
output "env" {
  value = join("\n", [
    "AWS_REGION=${local.region}",
    "AWS_BATCH_GPU_QUEUE=${aws_batch_job_queue.this["gpu-spot"].name}",
    "AWS_BATCH_CPU_QUEUE=${aws_batch_job_queue.this["cpu-spot"].name}",
    "AWS_S3_WORKDIR=s3://${aws_s3_bucket.batch.bucket}/work",
    "AWS_S3_OUTDIR=s3://${aws_s3_bucket.batch.bucket}/results",
  ])
}
