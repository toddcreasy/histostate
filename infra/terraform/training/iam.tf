# The role every Batch instance runs as. The ECS-for-EC2 managed policy lets the ECS agent
# register the instance and pull from ECR; SSM lets you open a shell on an instance without SSH.
# Nextflow's jobs run with these credentials, so S3 access is limited to this stack's bucket.
# Batch itself uses its service-linked role (AWSServiceRoleForBatch), so none is defined here.

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "${local.name}-batch-instance"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "instance_ecs" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "instance_ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "instance_bucket" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.batch.arn]
  }
  statement {
    sid = "ReadWriteObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = ["${aws_s3_bucket.batch.arn}/*"]
  }
}

resource "aws_iam_role_policy" "instance_bucket" {
  name   = "batch-bucket"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.instance_bucket.json
}

resource "aws_iam_instance_profile" "instance" {
  name = "${local.name}-batch-instance"
  role = aws_iam_role.instance.name
}
