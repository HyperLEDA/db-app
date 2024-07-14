from typing import Awaitable, Callable

import structlog
from aiohttp import web

from app.lib import auth, exceptions

log: structlog.stdlib.BoundLogger = structlog.get_logger()

AUTHORIZATION_HEADER = "Authorization"
AUTHORIZATION_PREFIX = "Bearer "


@web.middleware
async def exception_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    try:
        response = await handler(request)
    except exceptions.APIError as e:
        log.exception(str(e))
        response = web.json_response(e.dict(), status=e.status())
    except Exception as e:
        exc = exceptions.InternalError(str(e))
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
                raise exceptions.UnauthorizedError("No authorization header")

            token = request.headers[AUTHORIZATION_HEADER].removeprefix(AUTHORIZATION_PREFIX)
            user, is_authenticated = authenticator.authenticate(token)

            if not is_authenticated:
                raise exceptions.UnauthorizedError("Invalid token")

            if user.role != auth.Role.ADMIN:
                raise exceptions.ForbiddenError("Not enough permissions to access this method")

        return await handler(request)

    return auth_middleware
