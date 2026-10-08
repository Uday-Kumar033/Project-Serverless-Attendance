resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

data "archive_file" "backend" {
  type        = "zip"
  source_dir  = "${path.module}/../build/package"
  output_path = "${path.module}/../build/backend.zip"
}

locals {
  # rw / ro = tables the function may write / only read. sns = may send SMS.
  functions = {
    health = {
      handler = "functions.health.handler.lambda_handler"
      rw      = []
      ro      = []
      sns     = false
    }
    auth = {
      handler = "functions.auth.handler.lambda_handler"
      rw      = [aws_dynamodb_table.users.arn, aws_dynamodb_table.otp.arn]
      ro      = []
      sns     = true
    }
    attendance = {
      handler = "functions.attendance.handler.lambda_handler"
      rw      = [aws_dynamodb_table.attendance.arn, aws_dynamodb_table.classes.arn]
      ro      = [aws_dynamodb_table.users.arn]
      sns     = false
    }
  }

  functions_with_policy = {
    for k, v in local.functions : k => v if length(v.rw) + length(v.ro) > 0 || v.sns
  }
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "fn" {
  for_each           = local.functions
  name               = "attendance-${var.stage}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  for_each   = local.functions
  role       = aws_iam_role.fn[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "fn" {
  for_each = local.functions_with_policy

  dynamic "statement" {
    for_each = length(each.value.rw) > 0 ? [1] : []
    content {
      actions = [
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
        "dynamodb:Query", "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem",
      ]
      resources = concat(each.value.rw, [for a in each.value.rw : "${a}/index/*"])
    }
  }

  dynamic "statement" {
    for_each = length(each.value.ro) > 0 ? [1] : []
    content {
      actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"]
      resources = concat(each.value.ro, [for a in each.value.ro : "${a}/index/*"])
    }
  }

  dynamic "statement" {
    for_each = each.value.sns ? [1] : []
    content {
      actions   = ["sns:Publish"]
      resources = ["*"]
    }
  }
}

resource "aws_iam_role_policy" "fn" {
  for_each = local.functions_with_policy
  name     = "access"
  role     = aws_iam_role.fn[each.key].id
  policy   = data.aws_iam_policy_document.fn[each.key].json
}

resource "aws_cloudwatch_log_group" "fn" {
  for_each          = local.functions
  name              = "/aws/lambda/attendance-${var.stage}-${each.key}"
  retention_in_days = 14
}

resource "aws_lambda_function" "fn" {
  for_each         = local.functions
  function_name    = "attendance-${var.stage}-${each.key}"
  role             = aws_iam_role.fn[each.key].arn
  runtime          = "python3.12"
  handler          = each.value.handler
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256
  timeout          = 10
  memory_size      = 256

  environment {
    variables = {
      USERS_TABLE      = aws_dynamodb_table.users.name
      ATTENDANCE_TABLE = aws_dynamodb_table.attendance.name
      CLASSES_TABLE    = aws_dynamodb_table.classes.name
      OTP_TABLE        = aws_dynamodb_table.otp.name
      JWT_SECRET       = random_password.jwt_secret.result
      ALLOWED_ORIGIN   = var.allowed_origin
    }
  }

  depends_on = [aws_cloudwatch_log_group.fn, aws_iam_role_policy_attachment.logs]
}
