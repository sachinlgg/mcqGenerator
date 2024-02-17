variable "pagerduty_token" {
  description = "Token"
  default     = "u+N-_9m7WxFvDdNGRySg"
}

variable "pagerduty_account_email" {
  description = "email"
  default     = "apd@gooctoplus.com"
}

variable "pagerduty_account_first_name" {
  description = "email"
  default     = "A"
}

variable "pagerduty_account_second_name" {
  description = "email"
  default     = "PD"
}

variable "teams" {
  type = map(object({
    name    = string
    members = map(object({
      name  = string
      email = string
      phone = string
    }))
  }))
  default = {
    sre_team = {
      name    = "SRE"
      members = {
        aman = {
          name  = "Aman"
          email = "aman@gooctoplus.com"
          phone = "9021488747"
        }
        sachin = {
          name  = "Sachin"
          email = "sachin@gooctoplus.com"
          phone = "8708254121"
        }
      }
    }
    engineering_team = {
      name    = "Engineering"
      members = {
        earline = {
          name  = "Earline Greenholt"
          email = "125.greenholt.earline@gooctoplus.com"
          phone = "9021488747"
        }
        # Add more members as needed
      }
    }
    # Add more teams as needed
  }
}

variable "service_team_mapping" {
  type = map(string)
  default = {
    "payment service"    = "Engineering",
    "devops Service"     = "SRE",
    "Database Service"   = "SRE"
  }
}