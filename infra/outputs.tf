output "api_url" {
  value = aws_apigatewayv2_stage.stage.invoke_url
}

output "teacher_signup_code" {
  value     = random_password.teacher_code.result
  sensitive = true
}

output "frontend_url" {
  value = "http://${aws_eip.web.public_ip}"
}

output "frontend_bucket" {
  value = aws_s3_bucket.web.bucket
}

output "web_instance_id" {
  value = aws_instance.web.id
}

output "region" {
  value = var.region
}

output "github_deploy_role_arn" {
  value = one(aws_iam_role.github_deploy[*].arn)
}
