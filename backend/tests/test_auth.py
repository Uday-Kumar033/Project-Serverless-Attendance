import json
import os

import boto3
import pytest
from moto import mock_aws

os.environ.update(AWS_DEFAULT_REGION="ap-south-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
                  USERS_TABLE="users", ATTENDANCE_TABLE="att", CLASSES_TABLE="cls", OTP_TABLE="otp",
                  JWT_SECRET="x" * 48, ALLOWED_ORIGIN="*", TEACHER_SIGNUP_CODE="TEACH123")


@pytest.fixture
def handler():
    with mock_aws():
        boto3.client("dynamodb").create_table(
            TableName="users", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}])
        from functions.auth import handler as h
        yield h


def call(h, route, body):
    res = h.lambda_handler({"routeKey": route, "body": json.dumps(body)}, None)
    return res["statusCode"], json.loads(res["body"])


STUDENT = {"name": "Asha Rao", "email": "Asha@Example.com", "username": "Asha_01",
           "phone": "+919876543210", "role": "student", "password": "pass1234"}


def test_register_and_login_with_email_or_username(handler):
    assert call(handler, "POST /auth/register", STUDENT)[0] == 201
    for ident in ("asha@example.com", "ASHA_01"):
        status, data = call(handler, "POST /auth/login", {"identifier": ident, "password": "pass1234"})
        assert status == 200 and data["user"]["role"] == "student" and data["token"]


def test_duplicate_email_username_phone_rejected(handler):
    call(handler, "POST /auth/register", STUDENT)
    for change in ({"username": "other"}, {"email": "o@example.com", "phone": "+919876543211"},
                   {"email": "o@example.com", "username": "other"}):
        status, _ = call(handler, "POST /auth/register", {**STUDENT, **change})
        assert status == 409


def test_validation_and_teacher_code(handler):
    assert call(handler, "POST /auth/register", {**STUDENT, "password": "short"})[0] == 400
    assert call(handler, "POST /auth/register", {**STUDENT, "role": "teacher"})[0] == 400
    assert call(handler, "POST /auth/register", {**STUDENT, "role": "teacher", "teacherCode": "TEACH123"})[0] == 201


def test_wrong_password_then_lockout(handler):
    call(handler, "POST /auth/register", STUDENT)
    for _ in range(5):
        assert call(handler, "POST /auth/login", {"identifier": "asha_01", "password": "wrong"})[0] == 401
    assert call(handler, "POST /auth/login", {"identifier": "asha_01", "password": "pass1234"})[0] == 429
