import time
from collections.abc import Awaitable, Callable
from typing import Any

import fastapi
import structlog
from starlette import types
from starlette.middleware import base as middlewares


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

        data["headers"] = dict(r.headers)
        data["query"] = dict(r.query_params)

        data["url"] = str(r.base_url)
        data["path"] = r.path_params

        return data

    def _log_response(self, r: fastapi.Response) -> dict[str, Any]:
        data = {}

        data["headers"] = dict(r.headers)
        data["status_code"] = r.status_code

        return data

    async def dispatch(
        self, request: fastapi.Request, call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]]
    ) -> fastapi.Response:
        self.logger.info("HTTP request", **(await self._log_request(request)))

        start = time.perf_counter()
        response = await call_next(request)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        self.logger.info("HTTP response", elapsed_ms=elapsed_ms, **self._log_response(response))

        return response
