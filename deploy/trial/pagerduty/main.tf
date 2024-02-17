terraform {
  required_providers {
    pagerduty = {
      source  = "pagerduty/pagerduty"
      version = ">= 2.2.1"
    }
  }
  backend "s3" {
    bucket  = "gooctoplus-trial-accounts-pager-duty"
    key     = "gooctoplus-trial-accounts-pager-duty.tfstate"
    region  = "ap-south-1"
    encrypt = true
  }
}