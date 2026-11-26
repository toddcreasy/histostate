# The account's default VPC and its public subnets. The region is at its 5-VPC limit, so this
# stack does not create one. Public subnets give each instance a public IP, which is how it
# reaches ECR, S3, and Zenodo (the PathMNIST download) without a NAT gateway.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_security_group" "compute" {
  name        = "${local.name}-batch-compute"
  description = "AWS Batch compute instances: no inbound, egress only"
  vpc_id      = data.aws_vpc.default.id
}

# trivy:ignore:AWS-0104 Instances pull the image from ECR, PathMNIST from Zenodo, and read and write S3 over the internet; there is no NAT gateway or VPC endpoint to narrow this to. No inbound rule exists.
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.compute.id
  description       = "All outbound: ECR, S3, Zenodo"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
