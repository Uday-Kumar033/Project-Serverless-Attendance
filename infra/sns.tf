# Account-wide SMS settings for this region.
# The spend limit protects your free trial: SNS stops sending once $1 is spent this month.
resource "aws_sns_sms_preferences" "sms" {
  default_sms_type    = "Transactional"
  monthly_spend_limit = 1
}
