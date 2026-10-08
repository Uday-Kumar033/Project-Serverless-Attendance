terraform {
  # State lives in S3 so your computer and the CI pipeline share it. The bucket name and region
  # are supplied by scripts/tf-init.sh.
  backend "s3" {
    key          = "attendance/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_version = ">= 1.10"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.60" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "attendance-system", Stage = var.stage }
  }
}
