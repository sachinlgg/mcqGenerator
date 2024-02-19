provider "pagerduty" {
  token = var.pagerduty_token
}

# Create PagerDuty teams, users, and team memberships using a loop
resource "pagerduty_team" "teams" {
  for_each = var.teams

  name = each.value.name
}

#output "pagerduty_users" {
#  value = {
#  for team_name, team_details in var.teams : team_name => {
#  for member_name, member_details in team_details.members : member_name => {
#    name  = member_details.name
#    email = member_details.email
#  }
#  }
#  }
#}


# Create PagerDuty users for the SRE team
resource "pagerduty_user" "sre_team_users" {
  for_each = can(var.teams["sre_team"]) ? var.teams["sre_team"].members : {}
  name  = each.value.name
  email = each.value.email
}

# Create PagerDuty users for the Engineering team
resource "pagerduty_user" "engineering_team_users" {
  for_each = can(var.teams["engineering_team"]) ? var.teams["engineering_team"].members : {}

  name  = each.value.name
  email = each.value.email
}

# Create PagerDuty team memberships for the SRE team
resource "pagerduty_team_membership" "sre_team_memberships" {
  for_each = can(var.teams["sre_team"]) ? var.teams["sre_team"].members : {}

  user_id = pagerduty_user.sre_team_users[each.key].id
  team_id = pagerduty_team.teams["sre_team"].id
}

# Create PagerDuty team memberships for the Engineering team
resource "pagerduty_team_membership" "engineering_team_memberships" {
  for_each = can(var.teams["engineering_team"]) ? var.teams["engineering_team"].members : {}

  user_id = pagerduty_user.engineering_team_users[each.key].id
  team_id = pagerduty_team.teams["engineering_team"].id
}

## Create PagerDuty user contact methods (phone and SMS) for the SRE team users
#resource "pagerduty_user_contact_method" "sre_team_users_phone" {
#  for_each = can(var.teams["sre_team"]) ? var.teams["sre_team"].members : {}
#  user_id      = pagerduty_user.sre_team_users[each.key].id
#  type         = "phone_contact_method"
#  country_code = "+91"
#  address      = each.value.phone
#  label        = "Work"
#}
#
#resource "pagerduty_user_contact_method" "engineering_team_users_phone" {
#  for_each = can(var.teams["engineering_team"]) ? var.teams["engineering_team"].members : {}
#
#  user_id      = pagerduty_user.engineering_team_users[each.key].id
#  type         = "phone_contact_method"
#  country_code = "+91"
#  address      = each.value.phone
#  label        = "Work"
#}

# Create PagerDuty escalation policy for the SRE team
resource "pagerduty_escalation_policy" "sre_escalation_policy" {
  count     = can(var.teams["sre_team"]) ? 1 : 0
  name      = "SRE Escalation Policy"
  num_loops = 2
  teams     = [can(pagerduty_team.teams["sre_team"]) ? pagerduty_team.teams["sre_team"].id : null]

  dynamic "rule" {
    for_each = pagerduty_schedule.sre_schedule

    content {
      escalation_delay_in_minutes = 10
      target {
        type = "schedule_reference"
        id   = rule.value.id
      }
    }
  }
}

# Create PagerDuty escalation policy for the Engineering team
resource "pagerduty_escalation_policy" "engineering_escalation_policy" {
  count     = can(var.teams["engineering_team"]) ? 1 : 0
  name      = "Engineering Escalation Policy"
  num_loops = 2
  teams     = [can(pagerduty_team.teams["engineering_team"]) ? pagerduty_team.teams["engineering_team"].id : null]

  dynamic "rule" {
    for_each = pagerduty_schedule.engineering_schedule

    content {
      escalation_delay_in_minutes = 10
      target {
        type = "schedule_reference"
        id   = rule.value.id
      }
    }
  }
}

resource "pagerduty_schedule" "sre_schedule" {
  count     = can(var.teams["sre_team"]) ? 1 : 0
  name      = "Daily SRE Rotation"
  time_zone = "Asia/Kolkata"  # Set the time zone to Indian Standard Time (IST)

  layer {
    name                         = "Night Shift"
    start                        = "2024-02-16T00:00:00+05:30"  # Adjust the start time according to IST
    rotation_virtual_start       = "2024-02-16T00:00:00+05:30"  # Adjust the virtual start time according to IST
    rotation_turn_length_seconds = 86400
    users                        = can(pagerduty_team.teams["sre_team"]) ? [for user in pagerduty_user.sre_team_users : user.id] : []

    restriction {
      type              = "daily_restriction"
      start_time_of_day = "00:00:00"
      duration_seconds  = 86399
    }
  }

  teams = can(pagerduty_team.teams["sre_team"]) ? [pagerduty_team.teams["sre_team"].id] : []
}

resource "pagerduty_schedule" "engineering_schedule" {
  count     = can(var.teams["engineering_team"]) ? 1 : 0
  name      = "Daily Engineering Rotation"
  time_zone = "Asia/Kolkata"  # Set the time zone to Indian Standard Time (IST)

  layer {
    name                         = "Night Shift"
    start                        = "2024-02-16T00:00:00+05:30"  # Adjust the start time according to IST
    rotation_virtual_start       = "2024-02-16T00:00:00+05:30"  # Adjust the virtual start time according to IST
    rotation_turn_length_seconds = 86400
    users                        = can(pagerduty_team.teams["engineering_team"]) ? [for user in pagerduty_user.engineering_team_users : user.id] : []

    restriction {
      type              = "daily_restriction"
      start_time_of_day = "00:00:00"
      duration_seconds  = 86399
    }
  }

  teams = can(pagerduty_team.teams["engineering_team"]) ? [pagerduty_team.teams["engineering_team"].id] : []
}

# Create PagerDuty services based on the configuration map
locals {
  escalation_policies = {
    "SRE"        = can(pagerduty_team.teams["sre_team"]) ? pagerduty_escalation_policy.sre_escalation_policy[0].id : null
    "Engineering" = can(pagerduty_team.teams["engineering_team"]) ? pagerduty_escalation_policy.engineering_escalation_policy[0].id : null
    # Add more teams as needed
  }
}

resource "pagerduty_service" "services" {
  for_each = var.service_team_mapping

  name        = each.key
  description = "Service for ${each.key}"
  auto_resolve_timeout    = 14400
  acknowledgement_timeout = 600
  alert_creation          = "create_alerts_and_incidents"
  auto_pause_notifications_parameters {
    enabled = true
    timeout = 300
  }
  escalation_policy = local.escalation_policies[each.value]
}