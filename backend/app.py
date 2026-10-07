from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

USERS_FILE = "data/users.json"
ATTENDANCE_FILE = "data/attendance.json"


def read_json(file):
    with open(file, "r") as f:
        return json.load(f)


def write_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# -------------------------
# LOGIN
# -------------------------

@app.route("/api/login", methods=["POST"])
def login():

    data = request.json

    email = data.get("email")
    password = data.get("password")

    users = read_json(USERS_FILE)

    for user in users:

        if user["email"] == email and user["password"] == password:

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "userId": user["userId"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"]
                }
            })

    return jsonify({
        "success": False,
        "message": "Invalid email or password"
    }), 401


# -------------------------
# CHECK IN
# -------------------------

@app.route("/api/attendance/checkin", methods=["POST"])
def checkin():

    data = request.json

    user_id = data.get("userId")

    attendance = read_json(ATTENDANCE_FILE)

    today = datetime.now().strftime("%Y-%m-%d")

    # Prevent duplicate check-in
    for record in attendance:

        if (
            record["userId"] == user_id
            and record["date"] == today
        ):

            return jsonify({
                "success": False,
                "message": "Attendance already marked today"
            }), 400

    current_time = datetime.now().strftime("%H:%M:%S")

    record = {
        "userId": user_id,
        "date": today,
        "checkIn": current_time,
        "checkOut": None,
        "status": "Present"
    }

    attendance.append(record)

    write_json(ATTENDANCE_FILE, attendance)

    return jsonify({
        "success": True,
        "message": "Check-in successful",
        "attendance": record
    })


# -------------------------
# CHECK OUT
# -------------------------

@app.route("/api/attendance/checkout", methods=["POST"])
def checkout():

    data = request.json

    user_id = data.get("userId")

    attendance = read_json(ATTENDANCE_FILE)

    today = datetime.now().strftime("%Y-%m-%d")

    for record in attendance:

        if (
            record["userId"] == user_id
            and record["date"] == today
        ):

            if record["checkOut"]:

                return jsonify({
                    "success": False,
                    "message": "Already checked out"
                }), 400

            record["checkOut"] = datetime.now().strftime("%H:%M:%S")

            write_json(ATTENDANCE_FILE, attendance)

            return jsonify({
                "success": True,
                "message": "Check-out successful",
                "attendance": record
            })

    return jsonify({
        "success": False,
        "message": "Please check in first"
    }), 400


# -------------------------
# ATTENDANCE HISTORY
# -------------------------

@app.route("/api/attendance/<user_id>", methods=["GET"])
def history(user_id):

    attendance = read_json(ATTENDANCE_FILE)

    user_records = [
        record
        for record in attendance
        if record["userId"] == user_id
    ]

    return jsonify({
        "success": True,
        "attendance": user_records
    })


# -------------------------
# HEALTH CHECK
# -------------------------

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy",
        "service": "attendance-api"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
