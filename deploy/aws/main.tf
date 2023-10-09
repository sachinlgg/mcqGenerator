terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.48.0" # Optional but recommended in production
    }
  }
  backend "s3" {
    bucket         = "gooctoplus-ecs-demo"
    key            = "gooctoplus-ecs-demo.tfstate"
    region         = "ap-south-1"
    encrypt        = true
#    dynamodb_table = "gooctoplus-ecs-demo-tf-state-lock"
  }
}

provider "aws" {
  alias  = "ap-south-1"
  region = var.region
}

locals {
  prefix = "${var.prefix}-${terraform.workspace}"

  common_tags = {
    Environment = terraform.workspace
    Project     = var.project
    Owner       = var.contact
    ManagedBy   = "Terraform"
  }
}


resource "aws_ecr_repository" "gooctoplus_ecr_repo" {
  name = "gooctoplus-ecr-repo" # Naming my repository
}

data "aws_region" "current" {

}