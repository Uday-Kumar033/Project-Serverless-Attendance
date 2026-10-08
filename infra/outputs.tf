output "api_url" {
  value = aws_apigatewayv2_stage.stage.invoke_url
}

output "teacher_signup_code" {
  value     = random_password.teacher_code.result
  sensitive = true
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "frontend_bucket" {
  value = aws_s3_bucket.web.bucket
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.web.id
}

output "region" {
  value = var.region
}
