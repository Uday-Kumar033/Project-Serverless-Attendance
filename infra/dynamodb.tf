# Provisioned 2/2 on each table and index = 14 RCU/WCU total, inside the 25 always-free limit.

resource "aws_dynamodb_table" "users" {
  name           = "attendance-${var.stage}-users"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "attendance" {
  name           = "attendance-${var.stage}-attendance"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "studentId"
  range_key      = "sk"

  attribute {
    name = "studentId"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "classId"
    type = "S"
  }
  attribute {
    name = "date"
    type = "S"
  }

  global_secondary_index {
    name            = "class-date-index"
    hash_key        = "classId"
    range_key       = "date"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }
}

resource "aws_dynamodb_table" "classes" {
  name           = "attendance-${var.stage}-classes"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "classId"

  attribute {
    name = "classId"
    type = "S"
  }
  attribute {
    name = "teacherId"
    type = "S"
  }

  global_secondary_index {
    name            = "teacher-index"
    hash_key        = "teacherId"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }
}

resource "aws_dynamodb_table" "otp" {
  name           = "attendance-${var.stage}-otp"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "phone"

  attribute {
    name = "phone"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
}
