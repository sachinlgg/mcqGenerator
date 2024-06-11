variable "region" {
  description = "Region to create the AWS resources"
  default     = "ap-south-1"
}

variable "prefix" {
  default = "gooctoplus"
}


variable "project" {
  description = "Name of the project to be deployed on this infrastructure"
  default     = "gooctoplus-ecs-demo"
}

variable "contact" {
  description = "Email of the contact person responsible for this infrastructure"
  default     = "aman@gooctoplus.com"
}

variable "bot_key_name" {
  default = "gooctoplus-production-bot-ssh-key"
}

variable "db_username" {
  description = "Username for the RDS postgres instance"
  default = "gooctoplus_bot"
}

variable "db_password" {
  description = "Password for the RDS postgres instance"
  default = "gooctoplus_Tech_3003"
}

variable "ecr_image_api" {
  description = "ECR image for API"
  default     = "798229867165.dkr.ecr.ap-south-1.amazonaws.com/gooctoplus-ecr-repo:v14"
  // default     = "798229867165.dkr.ecr.ap-south-1.amazonaws.com/gooctoplus-ecr-repo:latest"
}

variable "dns_zone_name" {
  description = "Domain Name"
  default     = "gooctoplus.com"
}

variable "subdomain" {
  description = "Subdomain per environment"
  type        = map(string)
  default = {
    production = "api"
    staging    = "api.staging"
    dev        = "api.dev"
  }
}

variable "domain_name" {
  description = "Domain name"
  type        = string
  default     = "gooctoplus.com"
}