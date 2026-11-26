# Counts only resources tagged project=histostate (an active cost allocation tag). Tag data in
# Cost Explorer lags about a day, so treat this as a warning, not a brake. Credits are left out
# so they cannot hide real spend. Alerts at 50% and 80% of actual spend and 100% of forecast, as
# in ehr-rwe-eln and glia-nav.

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name = "TagKeyValue"
    # "user:<tag key>$<tag value>". Not "$${...}": that escapes to a literal "${" and the
    # name is never filled in (ehr-rwe-eln's budget shipped that way and matches nothing).
    values = [format("user:project$%s", local.name)]
  }

  cost_types {
    include_credit = false
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}
