from common.responses import ok


def lambda_handler(event, context):
    return ok({"status": "healthy"})
