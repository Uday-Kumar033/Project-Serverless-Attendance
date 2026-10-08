from common.responses import error

# Day 2: register + login. Day 4: forgot + reset (OTP).
ROUTES = {}


def lambda_handler(event, context):
    handler = ROUTES.get(event.get("routeKey"))
    if not handler:
        return error(501, "Not implemented yet")
    return handler(event)
