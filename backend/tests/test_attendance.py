import json
import os
from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

os.environ.update(AWS_DEFAULT_REGION="ap-south-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
                  USERS_TABLE="users", ATTENDANCE_TABLE="att", CLASSES_TABLE="cls", OTP_TABLE="otp",
                  JWT_SECRET="x" * 48, ALLOWED_ORIGIN="*", TEACHER_SIGNUP_CODE="TEACH123")

S = lambda n: {"AttributeName": n, "AttributeType": "S"}
H = lambda n: {"AttributeName": n, "KeyType": "HASH"}
R = lambda n: {"AttributeName": n, "KeyType": "RANGE"}


@pytest.fixture
def env():
    with mock_aws():
        c = boto3.client("dynamodb")
        c.create_table(TableName="users", BillingMode="PAY_PER_REQUEST",
                       AttributeDefinitions=[S("userId")], KeySchema=[H("userId")])
        c.create_table(TableName="cls", BillingMode="PAY_PER_REQUEST",
                       AttributeDefinitions=[S("classId"), S("teacherId")], KeySchema=[H("classId")],
                       GlobalSecondaryIndexes=[{"IndexName": "teacher-index", "KeySchema": [H("teacherId")],
                                                "Projection": {"ProjectionType": "ALL"}}])
        c.create_table(TableName="att", BillingMode="PAY_PER_REQUEST",
                       AttributeDefinitions=[S("studentId"), S("sk"), S("classId"), S("date")],
                       KeySchema=[H("studentId"), R("sk")],
                       GlobalSecondaryIndexes=[{"IndexName": "class-date-index",
                                                "KeySchema": [H("classId"), R("date")],
                                                "Projection": {"ProjectionType": "ALL"}}])
        from functions.attendance import handler as att
        from functions.auth import handler as auth
        yield auth, att


def call(h, route, body=None, token=None, path=None, qs=None):
    event = {"routeKey": route, "body": json.dumps(body) if body is not None else None,
             "headers": {"authorization": f"Bearer {token}"} if token else {},
             "pathParameters": path, "queryStringParameters": qs}
    res = h.lambda_handler(event, None)
    return res["statusCode"], json.loads(res["body"])


def signup(auth, username, role):
    body = {"name": username.title(), "email": f"{username}@example.com", "username": username,
            "phone": "+91" + str(abs(hash(username)) % 10**10).zfill(10), "role": role,
            "password": "pass1234", "teacherCode": "TEACH123"}
    assert call(auth, "POST /auth/register", body)[0] == 201
    return call(auth, "POST /auth/login", {"identifier": username, "password": "pass1234"})[1]


def test_full_flow(env):
    auth, att = env
    t1, t2 = signup(auth, "teacher1", "teacher")["token"], signup(auth, "teacher2", "teacher")["token"]
    s1, s2 = signup(auth, "student1", "student"), signup(auth, "student2", "student")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    status, data = call(att, "POST /classes", {"name": "Math 10A"}, t1)
    assert status == 201
    cid = data["class"]["classId"]
    path = {"classId": cid}
    assert call(att, "GET /classes", token=t1)[1]["classes"][0]["name"] == "Math 10A"
    assert call(att, "GET /classes", token=t2)[1]["classes"] == []

    # enrolling
    assert call(att, "POST /classes/{classId}/students", {"username": "Student1"}, t1, path)[0] == 201
    assert call(att, "POST /classes/{classId}/students", {"username": "student2"}, t1, path)[0] == 201
    assert call(att, "POST /classes/{classId}/students", {"username": "student1"}, t1, path)[0] == 409
    assert call(att, "POST /classes/{classId}/students", {"username": "nobody"}, t1, path)[0] == 404
    assert call(att, "POST /classes/{classId}/students", {"username": "teacher2"}, t1, path)[0] == 404
    assert call(att, "POST /classes/{classId}/students", {"username": "student1"}, t2, path)[0] == 404
    assert len(call(att, "GET /classes/{classId}/students", token=t1, path=path)[1]["students"]) == 2

    # marking
    records = [{"studentId": s1["user"]["userId"], "status": "present"},
               {"studentId": s2["user"]["userId"], "status": "absent"}]
    body = {"classId": cid, "date": today, "records": records}
    assert call(att, "POST /attendance", body, s1["token"])[0] == 403
    assert call(att, "POST /attendance", body, t2)[0] == 404
    assert call(att, "POST /attendance", {**body, "records": [{"studentId": "x", "status": "present"}]}, t1)[0] == 400
    assert call(att, "POST /attendance", {**body, "records": [{**records[0], "status": "late"}]}, t1)[0] == 400
    future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    assert call(att, "POST /attendance", {**body, "date": future}, t1)[0] == 400
    assert call(att, "POST /attendance", body, t1)[0] == 200

    day = call(att, "GET /attendance", token=t1, qs={"classId": cid, "date": today})[1]["records"]
    assert {r["status"] for r in day} == {"present", "absent"}
    assert call(att, "GET /attendance", token=t2, qs={"classId": cid, "date": today})[0] == 404

    # student sees only their own
    mine = call(att, "GET /attendance/me", token=s1["token"])[1]
    assert mine["summary"][0]["percentage"] == 100.0 and len(mine["records"]) == 1
    other = call(att, "GET /attendance/me", token=s2["token"])[1]
    assert other["summary"][0]["low"] is True
    assert call(att, "GET /attendance/me", token=t1)[0] == 403
    assert call(att, "GET /attendance/me")[0] == 401

    # teacher can correct a mark
    records[1]["status"] = "present"
    assert call(att, "POST /attendance", {**body, "records": records}, t1)[0] == 200
    assert call(att, "GET /attendance/me", token=s2["token"])[1]["summary"][0]["percentage"] == 100.0
