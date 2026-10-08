from common.responses import error

# Day 3: GET /attendance/me, POST /attendance, GET /attendance
ROUTES = {}


def lambda_handler(event, context):
    handler = ROUTES.get(event.get("routeKey"))
    if not handler:
        return error(501, "Not implemented yet")
    return handler(event)
