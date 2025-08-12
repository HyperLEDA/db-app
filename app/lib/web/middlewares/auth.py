from collections.abc import Awaitable, Callable

import fastapi
from starlette import types
from starlette.middleware import base as middlewares

from app.lib import auth
from app.lib.web import errors

AUTHORIZATION_HEADER = "Authorization"
AUTHORIZATION_PREFIX = "Bearer "


class AuthMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        authenticator: auth.Authenticator,
    ) -> None:
        self.auth = authenticator

        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        if AUTHORIZATION_HEADER not in request.headers:
            raise errors.UnauthorizedError("No authorization header")

        token = request.headers[AUTHORIZATION_HEADER].removeprefix(AUTHORIZATION_PREFIX)
        user, is_authenticated = self.auth.authenticate(token)

        if not is_authenticated:
            raise errors.UnauthorizedError("Invalid token")

        if user.role != auth.Role.ADMIN:
            raise errors.ForbiddenError("Not enough permissions to access this method")

        return await call_next(request)
