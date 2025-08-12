from collections.abc import Awaitable, Callable

import fastapi
from starlette.middleware import base as middlewares


class AuthMiddleware(middlewares.BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        return await super().dispatch(request, call_next)
