variable "pagerduty_token" {
  description = "Token"
  default     = "u+X42VLEoXtxzQV7ThPg"
}

variable "pagerduty_account_email" {
  description = "email"
  default     = "apd1@gooctoplus.com"
}

variable "pagerduty_account_first_name" {
  description = "First Name"
  default     = "A"
}

variable "pagerduty_account_second_name" {
  description = "Second Name"
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
      name    = "Growth Team"
      members = {
        earline = {
          name  = "Rahul"
          email = "rahul@gooctoplus.com"
          phone = "9021488747"
        }
      }
    }
    authentication_team = {
      name    = "Authentication Team"
      members = {
        earline = {
          name  = "Sachin"
          email = "sachin.121@gooctoplus.com"
          phone = "9021488747"
        }
      }
    }
  }
}

variable "service_team_mapping" {
  type = map(string)
  default = {
    "payment service"    = "Growth Team",
    "growth and campaign service"    = "Growth Team",
    "devops Service"     = "SRE",
    "Database Service"   = "SRE"
    "Authentication Service"   = "Authentication Team"
  }
}