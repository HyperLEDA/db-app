import time
from collections.abc import Awaitable, Callable
from typing import Any

import fastapi
import structlog
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.web.middlewares.auth import identity_from_request

_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "x-api-key"})


class LoggingMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        logger: structlog.stdlib.BoundLogger,
        log_bodies: bool = True,
    ) -> None:
        self.logger = logger
        self.log_bodies = log_bodies

        super().__init__(app)

    async def _log_request(self, r: fastapi.Request) -> dict[str, Any]:
        data = {}

        if self.log_bodies:
            data["body"] = await r.body()

        data["headers"] = {
            key: "<redacted>" if key.lower() in _SENSITIVE_HEADERS else value for key, value in r.headers.items()
        }
        data["query"] = dict(r.query_params)

        data["url"] = str(r.base_url)
        data["path"] = r.path_params

        return data

    def _log_response(self, r: fastapi.Response) -> dict[str, Any]:
        data = {}

        data["headers"] = dict(r.headers)
        data["status_code"] = r.status_code

        return data

    def _username(self, request: fastapi.Request) -> str | None:
        auth_ctx = identity_from_request(request)
        return auth_ctx.user.login if auth_ctx is not None else None

    async def dispatch(
        self, request: fastapi.Request, call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]]
    ) -> fastapi.Response:
        username = self._username(request)
        request_log = await self._log_request(request)
        if username is not None:
            request_log["username"] = username
        self.logger.info("HTTP request", **request_log)

        start = time.perf_counter()
        response = await call_next(request)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        response_log = self._log_response(response)
        if username is not None:
            response_log["username"] = username
        self.logger.info("HTTP response", elapsed_ms=elapsed_ms, **response_log)

        return response
