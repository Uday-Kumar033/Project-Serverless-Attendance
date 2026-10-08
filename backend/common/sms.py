"""Sends text messages through Amazon SNS.

OTP_DELIVERY=sms  -> real SMS via SNS (default).
OTP_DELIVERY=log  -> prints the message to CloudWatch Logs instead. For testing only;
                     it is refused when STAGE is "prod".
"""
import os

import boto3


def send_sms(phone: str, message: str) -> None:
    if os.environ.get("OTP_DELIVERY", "sms") == "log":
        if os.environ.get("STAGE") == "prod":
            raise RuntimeError("OTP_DELIVERY=log is not allowed in prod")
        print(f"[DEV ONLY] SMS to {phone}: {message}")
        return
    boto3.client("sns").publish(
        PhoneNumber=phone,
        Message=message,
        MessageAttributes={"AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}},
    )
