"""Register, login, and password reset with a mobile OTP.

Users table layout
  - one real item per user:        userId = <uuid>
  - one "lookup" item per unique:  userId = EMAIL#<email> | USERNAME#<name> | PHONE#<number>
    each lookup item stores `ref` = the real userId.
Writing the user and its lookup items in ONE transaction guarantees no two
people can ever share an email, username or phone number.
"""
import hashlib
import hmac
import logging
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from common import db
from common.auth import create_token, hash_password, verify_password
from common.responses import error, ok, parse_body
from common.sms import send_sms

log = logging.getLogger()
log.setLevel(logging.INFO)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
PHONE_RE = re.compile(r"^\+[1-9]\d{9,14}$")  # international format, e.g. +919876543210
ROLES = {"student", "teacher"}

MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60

CODE_TTL_SECONDS = 5 * 60       # how long an OTP works
RESEND_COOLDOWN_SECONDS = 60    # minimum gap between two codes for one number
MAX_SENDS_PER_HOUR = 5
MAX_OTP_ATTEMPTS = 5
PASSWORD_MESSAGE = "Password needs at least 8 characters, with a letter and a number."

# Used so "unknown user" takes as long as "wrong password" (prevents user-guessing by timing).
_DUMMY_HASH = hash_password("not-a-real-password")


def _clean(body, key):
    value = body.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _password_ok(password):
    return len(password) >= 8 and re.search(r"[A-Za-z]", password) and re.search(r"\d", password)


def _validate(data, password, teacher_code):
    errors = {}
    if len(data["name"]) < 2 or len(data["name"]) > 60:
        errors["name"] = "Enter your full name (2 to 60 characters)."
    if not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address."
    if not USERNAME_RE.match(data["username"]):
        errors["username"] = "Username must be 3 to 20 characters: letters, numbers or underscore."
    if not PHONE_RE.match(data["phone"]):
        errors["phone"] = "Enter your phone number with country code, like +919876543210."
    if data["role"] not in ROLES:
        errors["role"] = "Choose student or teacher."
    if not _password_ok(password):
        errors["password"] = PASSWORD_MESSAGE
    if data["role"] == "teacher":
        expected = os.environ.get("TEACHER_SIGNUP_CODE", "")
        if not expected or not hmac.compare_digest(teacher_code.encode(), expected.encode()):
            errors["teacherCode"] = "Teacher sign-up code is incorrect."
    return errors


def register(event):
    body = parse_body(event)
    if body is None:
        return error(400, "Request body must be valid JSON.")

    data = {
        "name": _clean(body, "name"),
        "email": _clean(body, "email").lower(),
        "username": _clean(body, "username").lower(),
        "phone": _clean(body, "phone").replace(" ", ""),
        "role": _clean(body, "role"),
    }
    password = body.get("password") if isinstance(body.get("password"), str) else ""
    errors = _validate(data, password, _clean(body, "teacherCode"))
    if errors:
        return ok({"error": "Please fix the highlighted fields.", "fields": errors}, 400)

    table = db.users()
    user_id = str(uuid.uuid4())
    user_item = {
        "userId": user_id,
        **data,
        "passwordHash": hash_password(password),
        "failedAttempts": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    not_exists = "attribute_not_exists(userId)"
    lookups = [("email", f"EMAIL#{data['email']}"), ("username", f"USERNAME#{data['username']}"),
               ("phone", f"PHONE#{data['phone']}")]
    items = [{"Put": {"TableName": table.name, "Item": user_item, "ConditionExpression": not_exists}}]
    for _, key in lookups:
        items.append({"Put": {"TableName": table.name, "Item": {"userId": key, "ref": user_id},
                              "ConditionExpression": not_exists}})

    try:
        table.meta.client.transact_write_items(TransactItems=items)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "TransactionCanceledException":
            reasons = exc.response.get("CancellationReasons", [])
            for (field, _), reason in zip(lookups, reasons[1:]):
                if reason.get("Code") == "ConditionalCheckFailed":
                    label = {"email": "email", "username": "username", "phone": "phone number"}[field]
                    return ok({"error": f"That {label} is already registered.",
                               "fields": {field: f"This {label} is already in use."}}, 409)
        raise

    return ok({"message": "Account created. You can sign in now."}, 201)


def _find_user(identifier):
    table = db.users()
    prefix = "EMAIL#" if "@" in identifier else "USERNAME#"
    lookup = table.get_item(Key={"userId": prefix + identifier.lower()}, ConsistentRead=True).get("Item")
    if not lookup:
        return None
    return table.get_item(Key={"userId": lookup["ref"]}, ConsistentRead=True).get("Item")


def login(event):
    body = parse_body(event)
    if body is None:
        return error(400, "Request body must be valid JSON.")
    identifier = _clean(body, "identifier")
    password = body.get("password") if isinstance(body.get("password"), str) else ""
    if not identifier or not password:
        return error(400, "Enter your email or username and your password.")

    user = _find_user(identifier)
    if not user:
        verify_password(password, _DUMMY_HASH)
        return error(401, "Email/username or password is incorrect.")

    now = int(time.time())
    locked_until = int(user.get("lockedUntil", 0))
    if locked_until > now:
        minutes = (locked_until - now + 59) // 60
        return error(429, f"Too many failed attempts. Try again in {minutes} minute(s).")

    table = db.users()
    if not verify_password(password, user["passwordHash"]):
        attempts = int(user.get("failedAttempts", 0)) + 1
        if attempts >= MAX_FAILED_ATTEMPTS:
            table.update_item(Key={"userId": user["userId"]},
                              UpdateExpression="SET failedAttempts = :z, lockedUntil = :l",
                              ExpressionAttributeValues={":z": 0, ":l": now + LOCK_SECONDS})
        else:
            table.update_item(Key={"userId": user["userId"]},
                              UpdateExpression="SET failedAttempts = :a",
                              ExpressionAttributeValues={":a": attempts})
        return error(401, "Email/username or password is incorrect.")

    if user.get("failedAttempts") or user.get("lockedUntil"):
        table.update_item(Key={"userId": user["userId"]},
                          UpdateExpression="SET failedAttempts = :z REMOVE lockedUntil",
                          ExpressionAttributeValues={":z": 0})

    return ok({
        "token": create_token(user["userId"], user["role"]),
        "user": {"userId": user["userId"], "name": user["name"], "role": user["role"],
                 "username": user["username"], "email": user["email"]},
    })


# ---------- forgot / reset password (mobile OTP) ----------
def _hash_otp(phone, code):
    """Only a keyed hash of the code is stored, never the code itself."""
    return hmac.new(os.environ["JWT_SECRET"].encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def forgot(event):
    body = parse_body(event)
    if body is None:
        return error(400, "Request body must be valid JSON.")
    phone = _clean(body, "phone").replace(" ", "")
    if not PHONE_RE.match(phone):
        return error(400, "Enter your phone number with country code, like +919876543210.")

    now = int(time.time())
    otp_table = db.otp()
    state = otp_table.get_item(Key={"phone": phone}, ConsistentRead=True).get("Item") or {}
    hour_start, sends = int(state.get("hourStart", 0)), int(state.get("sends", 0))
    if now - hour_start >= 3600:
        hour_start, sends = now, 0
    # Same limits apply to every number, so this never reveals who is registered.
    if now - int(state.get("sentAt", 0)) < RESEND_COOLDOWN_SECONDS:
        return error(429, "Please wait a minute before asking for another code.")
    if sends >= MAX_SENDS_PER_HOUR:
        return error(429, "Too many code requests. Please try again in an hour.")

    code = f"{secrets.randbelow(10**6):06d}"
    otp_table.put_item(Item={
        "phone": phone, "otpHash": _hash_otp(phone, code), "codeExpiresAt": now + CODE_TTL_SECONDS,
        "attempts": 0, "sentAt": now, "hourStart": hour_start, "sends": sends + 1,
        "expiresAt": max(hour_start + 3600, now + CODE_TTL_SECONDS),  # DynamoDB TTL cleans this up
    })

    if db.users().get_item(Key={"userId": f"PHONE#{phone}"}).get("Item"):
        try:
            send_sms(phone, f"Your attendance app code is {code}. It expires in 5 minutes. Do not share it.")
        except Exception:  # never tell the caller whether sending worked
            log.exception("Could not send OTP SMS")

    return ok({"message": "If this number is registered, a 6-digit code is on its way."})


def reset_password(event):
    body = parse_body(event)
    if body is None:
        return error(400, "Request body must be valid JSON.")
    phone = _clean(body, "phone").replace(" ", "")
    code = _clean(body, "otp")
    new_password = body.get("newPassword") if isinstance(body.get("newPassword"), str) else ""
    invalid = error(400, "That code is incorrect or has expired. Ask for a new one.")

    if not PHONE_RE.match(phone) or not re.fullmatch(r"\d{6}", code):
        return error(400, "Enter the 6-digit code we sent you.")
    if not _password_ok(new_password):
        return ok({"error": PASSWORD_MESSAGE, "fields": {"password": PASSWORD_MESSAGE}}, 400)

    now = int(time.time())
    otp_table = db.otp()
    item = otp_table.get_item(Key={"phone": phone}, ConsistentRead=True).get("Item")
    if (not item or "otpHash" not in item or now > int(item["codeExpiresAt"])
            or int(item["attempts"]) >= MAX_OTP_ATTEMPTS):
        return invalid

    if not hmac.compare_digest(item["otpHash"], _hash_otp(phone, code)):
        otp_table.update_item(Key={"phone": phone}, UpdateExpression="ADD attempts :one",
                              ExpressionAttributeValues={":one": 1})
        return invalid

    users = db.users()
    lookup = users.get_item(Key={"userId": f"PHONE#{phone}"}).get("Item")
    if not lookup:
        return invalid

    # Use the code up first (atomic), so the same code can never work twice.
    try:
        otp_table.update_item(Key={"phone": phone}, UpdateExpression="REMOVE otpHash",
                              ConditionExpression="otpHash = :h",
                              ExpressionAttributeValues={":h": item["otpHash"]})
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return invalid
        raise

    users.update_item(Key={"userId": lookup["ref"]},
                      UpdateExpression="SET passwordHash = :h, failedAttempts = :z REMOVE lockedUntil",
                      ExpressionAttributeValues={":h": hash_password(new_password), ":z": 0})
    return ok({"message": "Password changed. You can sign in now."})


ROUTES = {
    "POST /auth/register": register,
    "POST /auth/login": login,
    "POST /auth/forgot": forgot,
    "POST /auth/reset": reset_password,
}


def lambda_handler(event, context):
    handler = ROUTES.get(event.get("routeKey"))
    if not handler:
        return error(501, "Not implemented yet")
    return handler(event)
