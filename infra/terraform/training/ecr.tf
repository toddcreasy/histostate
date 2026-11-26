# The training image registry. Each image is tagged with the git commit it was built from, and
# tags are immutable, so a tag always names the same image. Old images expire so storage stays
# small. Same settings as ehr-rwe-eln's app registry.

resource "aws_ecr_repository" "training" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "training" {
  repository = aws_ecr_repository.training.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "keep the 10 newest images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
