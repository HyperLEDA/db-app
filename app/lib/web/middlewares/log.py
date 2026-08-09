import time
import uuid
from collections.abc import Awaitable, Callable, Collection
from typing import Any

import fastapi
import structlog
from opentelemetry import trace
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.web.middlewares.auth import identity_from_request

_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "x-api-key"})


def _request_id() -> str:
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return str(uuid.uuid4())


def _client_ip(request: fastapi.Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip() or None

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None

    if request.client is None:
        return None
    return request.client.host


class LoggingMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        logger: structlog.stdlib.BoundLogger,
        log_bodies: Collection[tuple[str, str]] = (),
    ) -> None:
        self.logger = logger
        self._log_bodies = frozenset(log_bodies)

        super().__init__(app)

    async def _log_request(self, r: fastapi.Request) -> dict[str, Any]:
        data = {}

        if (r.url.path, r.method.lower()) in self._log_bodies:
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
        structlog.contextvars.clear_contextvars()
        client_ip = _client_ip(request)
        context: dict[str, str] = {"request_id": _request_id()}
        if client_ip is not None:
            context["client_ip"] = client_ip
        structlog.contextvars.bind_contextvars(**context)
        try:
            username = self._username(request)
            request_log = await self._log_request(request)
            if username is not None:
                request_log["username"] = username
            if client_ip is not None:
                request_log["client_ip"] = client_ip
            self.logger.info("HTTP request", **request_log)

            start = time.perf_counter()
            response = await call_next(request)
            end = time.perf_counter()

            elapsed_ms = (end - start) * 1000

            response_log = self._log_response(response)
            if username is not None:
                response_log["username"] = username
            if client_ip is not None:
                response_log["client_ip"] = client_ip
            self.logger.info("HTTP response", elapsed_ms=elapsed_ms, **response_log)

            return response
        finally:
            structlog.contextvars.clear_contextvars()
