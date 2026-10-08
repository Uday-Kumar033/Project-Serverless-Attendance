import json
import os
import re

import boto3
import pytest
from moto import mock_aws

os.environ.update(AWS_DEFAULT_REGION="ap-south-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
                  USERS_TABLE="users", ATTENDANCE_TABLE="att", CLASSES_TABLE="cls", OTP_TABLE="otp",
                  JWT_SECRET="x" * 48, ALLOWED_ORIGIN="*", TEACHER_SIGNUP_CODE="TEACH123")

PHONE = "+919876543210"
USER = {"name": "Asha Rao", "email": "asha@example.com", "username": "asha", "phone": PHONE,
        "role": "student", "password": "oldpass123"}


@pytest.fixture
def env(monkeypatch):
    with mock_aws():
        c = boto3.client("dynamodb")
        for name, key in (("users", "userId"), ("otp", "phone")):
            c.create_table(TableName=name, BillingMode="PAY_PER_REQUEST",
                           AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
                           KeySchema=[{"AttributeName": key, "KeyType": "HASH"}])
        from functions.auth import handler as auth
        sent = []
        monkeypatch.setattr(auth, "send_sms", lambda phone, msg: sent.append((phone, msg)))
        assert call(auth, "POST /auth/register", USER)[0] == 201
        yield auth, sent


def call(h, route, body):
    res = h.lambda_handler({"routeKey": route, "body": json.dumps(body)}, None)
    return res["statusCode"], json.loads(res["body"])


def code_from(sent):
    return re.search(r"\b(\d{6})\b", sent[-1][1]).group(1)


def expire_cooldown():
    boto3.resource("dynamodb").Table("otp").update_item(
        Key={"phone": PHONE}, UpdateExpression="SET sentAt = :t", ExpressionAttributeValues={":t": 0})


def test_reset_flow_and_code_is_single_use(env):
    auth, sent = env
    assert call(auth, "POST /auth/forgot", {"phone": PHONE})[0] == 200
    code = code_from(sent)
    assert call(auth, "POST /auth/reset", {"phone": PHONE, "otp": code, "newPassword": "short"})[0] == 400
    assert call(auth, "POST /auth/reset", {"phone": PHONE, "otp": code, "newPassword": "newpass123"})[0] == 200
    assert call(auth, "POST /auth/login", {"identifier": "asha", "password": "newpass123"})[0] == 200
    assert call(auth, "POST /auth/login", {"identifier": "asha", "password": "oldpass123"})[0] == 401
    assert call(auth, "POST /auth/reset", {"phone": PHONE, "otp": code, "newPassword": "another123"})[0] == 400


def test_unknown_number_gets_same_answer_and_no_sms(env):
    auth, sent = env
    status, data = call(auth, "POST /auth/forgot", {"phone": "+919000000000"})
    assert status == 200 and "registered" in data["message"] and sent == []
    assert call(auth, "POST /auth/reset", {"phone": "+919000000000", "otp": "123456",
                                           "newPassword": "newpass123"})[0] == 400


def test_resend_cooldown(env):
    auth, sent = env
    assert call(auth, "POST /auth/forgot", {"phone": PHONE})[0] == 200
    assert call(auth, "POST /auth/forgot", {"phone": PHONE})[0] == 429
    expire_cooldown()
    assert call(auth, "POST /auth/forgot", {"phone": PHONE})[0] == 200
    assert len(sent) == 2


def test_five_wrong_codes_lock_the_code(env):
    auth, sent = env
    call(auth, "POST /auth/forgot", {"phone": PHONE})
    right = code_from(sent)
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(5):
        assert call(auth, "POST /auth/reset", {"phone": PHONE, "otp": wrong, "newPassword": "newpass123"})[0] == 400
    assert call(auth, "POST /auth/reset", {"phone": PHONE, "otp": right, "newPassword": "newpass123"})[0] == 400


def test_reset_clears_login_lockout(env):
    auth, sent = env
    for _ in range(5):
        call(auth, "POST /auth/login", {"identifier": "asha", "password": "wrong"})
    assert call(auth, "POST /auth/login", {"identifier": "asha", "password": "oldpass123"})[0] == 429
    call(auth, "POST /auth/forgot", {"phone": PHONE})
    call(auth, "POST /auth/reset", {"phone": PHONE, "otp": code_from(sent), "newPassword": "newpass123"})
    assert call(auth, "POST /auth/login", {"identifier": "asha", "password": "newpass123"})[0] == 200
