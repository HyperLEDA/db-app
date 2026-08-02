from collections.abc import Awaitable, Callable

import fastapi
from opentelemetry import trace
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.web.middlewares.auth import identity_from_request

_USERNAME_ATTR = "username"


class TracingMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(self, app: types.ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        response = await call_next(request)

        auth_ctx = identity_from_request(request)
        if auth_ctx is None:
            return response

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute(_USERNAME_ATTR, auth_ctx.user.login)

        return response
