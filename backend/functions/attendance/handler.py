"""Classes and attendance.

Teacher: create classes, add students by username, mark and view attendance.
Student: view only their own attendance.

Attendance table: one item per student per class per day
  studentId (partition key) + sk = "<classId>#<date>"
The class-date-index lets a teacher fetch a whole class for one day.
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from common import db
from common.auth import get_claims
from common.responses import error, ok, parse_body

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUSES = {"present", "absent"}
LOW_ATTENDANCE_PERCENT = 75
MAX_RECORDS_PER_REQUEST = 500


# ---------- helpers ----------
def _auth(event, role):
    claims = get_claims(event)
    if not claims:
        return None, error(401, "Your session has ended. Please sign in again.")
    if claims.get("role") != role:
        return None, error(403, "You don't have access to this.")
    return claims, None


def _valid_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return False
    # allow today (any timezone) but not further in the future
    return parsed <= (datetime.now(timezone.utc) + timedelta(days=1)).date()


def _query_all(table, **kwargs):
    items = []
    while True:
        page = table.query(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _own_class(class_id, teacher_id):
    item = db.classes().get_item(Key={"classId": class_id}, ConsistentRead=True).get("Item")
    if not item or item["teacherId"] != teacher_id:
        return None
    return item


def _path_class_id(event):
    return (event.get("pathParameters") or {}).get("classId", "")


def _students(student_ids):
    """Fetch id, name and username for a list of user ids."""
    if not student_ids:
        return []
    users = db.users()
    client = users.meta.client
    found = []
    for start in range(0, len(student_ids), 100):
        keys = [{"userId": uid} for uid in student_ids[start:start + 100]]
        request = {users.name: {"Keys": keys, "ProjectionExpression": "userId, #n, username",
                                "ExpressionAttributeNames": {"#n": "name"}}}
        while request:
            result = client.batch_get_item(RequestItems=request)
            found.extend(result["Responses"].get(users.name, []))
            request = result.get("UnprocessedKeys") or None
    return sorted(found, key=lambda s: s["name"].lower())


# ---------- teacher: classes ----------
def create_class(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    body = parse_body(event) or {}
    name = body.get("name", "").strip() if isinstance(body.get("name"), str) else ""
    if not 2 <= len(name) <= 60:
        return error(400, "Class name must be 2 to 60 characters.")
    item = {"classId": uuid.uuid4().hex[:8], "name": name, "teacherId": claims["sub"],
            "studentIds": [], "createdAt": datetime.now(timezone.utc).isoformat()}
    db.classes().put_item(Item=item, ConditionExpression="attribute_not_exists(classId)")
    return ok({"class": {"classId": item["classId"], "name": name, "studentCount": 0}}, 201)


def list_classes(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    items = _query_all(db.classes(), IndexName="teacher-index",
                       KeyConditionExpression=Key("teacherId").eq(claims["sub"]))
    classes = [{"classId": c["classId"], "name": c["name"], "studentCount": len(c.get("studentIds", []))}
               for c in items]
    return ok({"classes": sorted(classes, key=lambda c: c["name"].lower())})


def add_student(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    cls = _own_class(_path_class_id(event), claims["sub"])
    if not cls:
        return error(404, "Class not found.")
    body = parse_body(event) or {}
    username = body.get("username", "").strip().lower() if isinstance(body.get("username"), str) else ""
    if not username:
        return error(400, "Enter the student's username.")

    users = db.users()
    lookup = users.get_item(Key={"userId": f"USERNAME#{username}"}).get("Item")
    student = users.get_item(Key={"userId": lookup["ref"]}).get("Item") if lookup else None
    if not student or student["role"] != "student":
        return error(404, "No student found with that username.")

    try:
        db.classes().update_item(
            Key={"classId": cls["classId"]},
            UpdateExpression="SET studentIds = list_append(studentIds, :new)",
            ConditionExpression="NOT contains(studentIds, :sid)",
            ExpressionAttributeValues={":new": [student["userId"]], ":sid": student["userId"]})
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error(409, f"{student['name']} is already in this class.")
        raise
    return ok({"student": {"userId": student["userId"], "name": student["name"],
                           "username": student["username"]}}, 201)


def list_roster(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    cls = _own_class(_path_class_id(event), claims["sub"])
    if not cls:
        return error(404, "Class not found.")
    return ok({"students": _students(cls.get("studentIds", []))})


# ---------- teacher: mark and view ----------
def mark_attendance(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    body = parse_body(event)
    if not isinstance(body, dict):
        return error(400, "Request body must be valid JSON.")
    class_id, date, records = body.get("classId"), body.get("date"), body.get("records")

    if not isinstance(class_id, str) or not _valid_date(date):
        return error(400, "Choose a class and a valid date (not in the future).")
    if not isinstance(records, list) or not 0 < len(records) <= MAX_RECORDS_PER_REQUEST:
        return error(400, "Mark at least one student.")
    cls = _own_class(class_id, claims["sub"])
    if not cls:
        return error(404, "Class not found.")

    roster = set(cls.get("studentIds", []))
    marks = {}
    for rec in records:
        if not isinstance(rec, dict) or rec.get("status") not in STATUSES:
            return error(400, "Each student must be marked present or absent.")
        if rec.get("studentId") not in roster:
            return error(400, "One of the students is not in this class.")
        marks[rec["studentId"]] = rec["status"]

    now = datetime.now(timezone.utc).isoformat()
    with db.attendance().batch_writer() as batch:
        for student_id, status in marks.items():
            batch.put_item(Item={
                "studentId": student_id, "sk": f"{class_id}#{date}", "classId": class_id,
                "className": cls["name"], "date": date, "status": status,
                "markedBy": claims["sub"], "markedAt": now})
    return ok({"message": f"Attendance saved for {len(marks)} student(s).", "saved": len(marks)})


def list_attendance(event):
    claims, err = _auth(event, "teacher")
    if err:
        return err
    params = event.get("queryStringParameters") or {}
    class_id, date = params.get("classId", ""), params.get("date", "")
    if not class_id or not _valid_date(date):
        return error(400, "Choose a class and a valid date.")
    if not _own_class(class_id, claims["sub"]):
        return error(404, "Class not found.")
    items = _query_all(db.attendance(), IndexName="class-date-index",
                       KeyConditionExpression=Key("classId").eq(class_id) & Key("date").eq(date))
    return ok({"records": [{"studentId": i["studentId"], "status": i["status"], "date": i["date"]}
                           for i in items]})


# ---------- student: own attendance only ----------
def my_attendance(event):
    claims, err = _auth(event, "student")
    if err:
        return err
    items = _query_all(db.attendance(), KeyConditionExpression=Key("studentId").eq(claims["sub"]))

    summary = {}
    for i in items:
        row = summary.setdefault(i["classId"], {"classId": i["classId"], "className": i["className"],
                                                "present": 0, "absent": 0})
        row[i["status"]] += 1
    for row in summary.values():
        row["total"] = row["present"] + row["absent"]
        row["percentage"] = round(row["present"] / row["total"] * 100, 1) if row["total"] else 0
        row["low"] = row["percentage"] < LOW_ATTENDANCE_PERCENT

    records = sorted(({"classId": i["classId"], "className": i["className"], "date": i["date"],
                       "status": i["status"]} for i in items), key=lambda r: r["date"], reverse=True)
    return ok({"summary": sorted(summary.values(), key=lambda r: r["className"].lower()),
               "records": records})


ROUTES = {
    "POST /classes": create_class,
    "GET /classes": list_classes,
    "POST /classes/{classId}/students": add_student,
    "GET /classes/{classId}/students": list_roster,
    "POST /attendance": mark_attendance,
    "GET /attendance": list_attendance,
    "GET /attendance/me": my_attendance,
}


def lambda_handler(event, context):
    handler = ROUTES.get(event.get("routeKey"))
    if not handler:
        return error(501, "Not implemented yet")
    return handler(event)
