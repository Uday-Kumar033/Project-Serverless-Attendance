import os
import boto3

_dynamodb = boto3.resource("dynamodb")


def table(env_name):
    return _dynamodb.Table(os.environ[env_name])


users = lambda: table("USERS_TABLE")
attendance = lambda: table("ATTENDANCE_TABLE")
classes = lambda: table("CLASSES_TABLE")
otp = lambda: table("OTP_TABLE")
