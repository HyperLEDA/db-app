import http
from collections.abc import Awaitable, Callable

import structlog
from aiohttp import web

from app.lib import auth
from app.lib.web import errors

log: structlog.stdlib.BoundLogger = structlog.get_logger()

AUTHORIZATION_HEADER = "Authorization"
AUTHORIZATION_PREFIX = "Bearer "


@web.middleware
async def exception_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    try:
        response = await handler(request)
    except errors.APIError as e:
        log.exception(str(e))
        response = web.json_response(e.dict(), status=e.status())
    except Exception as e:
        if isinstance(e, web.HTTPException):
            exc = errors.APIError.from_http_exception(e)
        else:
            exc = errors.InternalError(str(e))

        log.exception(str(exc))
        response = web.json_response(exc.dict(), status=500)

    return response


def get_auth_middleware(
    admin_prefix: str, authenticator: auth.Authenticator
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    @web.middleware
    async def auth_middleware(
        request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
    ) -> web.StreamResponse:
        if request.path.startswith(admin_prefix):
            if AUTHORIZATION_HEADER not in request.headers:
                raise errors.UnauthorizedError("No authorization header")

            token = request.headers[AUTHORIZATION_HEADER].removeprefix(AUTHORIZATION_PREFIX)
            user, is_authenticated = authenticator.authenticate(token)

            if not is_authenticated:
                raise errors.UnauthorizedError("Invalid token")

            if user.role != auth.Role.ADMIN:
                raise errors.ForbiddenError("Not enough permissions to access this method")

        return await handler(request)

    return auth_middleware


@web.middleware
async def cors_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    if request.method == http.HTTPMethod.OPTIONS:
        resp = web.Response(text="OK")
    else:
        resp = await handler(request)

    allowed_methods = [
        http.HTTPMethod.GET,
        http.HTTPMethod.POST,
        http.HTTPMethod.PUT,
        http.HTTPMethod.DELETE,
        http.HTTPMethod.OPTIONS,
    ]

    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = ",".join(allowed_methods)
    "GET,POST,PUT,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp
