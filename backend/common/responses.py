import json
import os


def _headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
    }


def respond(status, body):
    return {"statusCode": status, "headers": _headers(), "body": json.dumps(body, default=str)}


def ok(body, status=200):
    return respond(status, body)


def error(status, message):
    return respond(status, {"error": message})


def parse_body(event):
    try:
        return json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return None
