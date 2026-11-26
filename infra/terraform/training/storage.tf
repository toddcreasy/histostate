# One bucket for Nextflow: work/ is its scratch space (expires after 30 days) and results/ holds
# checkpoints, logs, and trace files. Private, TLS only. Not versioned: results are written once
# per run and the final model is also a GitHub release asset.

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "batch" {
  bucket = "${local.name}-batch-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "batch" {
  bucket                  = aws_s3_bucket.batch.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "batch" {
  bucket = aws_s3_bucket.batch.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# trivy:ignore:AWS-0132 SSE-S3 rather than a customer managed key ($1/month); the bucket is private and TLS only.
resource "aws_s3_bucket_server_side_encryption_configuration" "batch" {
  bucket = aws_s3_bucket.batch.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Refuse any request that isn't over TLS.
data "aws_iam_policy_document" "batch_tls_only" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.batch.arn, "${aws_s3_bucket.batch.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "batch" {
  bucket     = aws_s3_bucket.batch.id
  policy     = data.aws_iam_policy_document.batch_tls_only.json
  depends_on = [aws_s3_bucket_public_access_block.batch]
}

resource "aws_s3_bucket_lifecycle_configuration" "batch" {
  bucket = aws_s3_bucket.batch.id
  rule {
    id     = "expire-work"
    status = "Enabled"
    filter {
      prefix = "work/"
    }
    expiration {
      days = 30
    }
  }
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
