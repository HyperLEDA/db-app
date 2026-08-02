import unittest
from collections.abc import Awaitable, Callable
from unittest import mock

import fastapi
import structlog
from fastapi import testclient
from starlette.middleware import base as middlewares

from app.lib import auth
from app.lib.web.middlewares.auth import AUTH_CTX_STATE_ATTR, AuthContext
from app.lib.web.middlewares.log import LoggingMiddleware


class LoggingMiddlewareTest(unittest.TestCase):
    def test_request_headers_are_redacted(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)

        app.add_api_route("/ping", endpoint=lambda: {"ping": "pong"}, methods=["GET"])

        client = testclient.TestClient(app)
        response = client.get(
            "/ping",
            headers={
                "Authorization": "Bearer secret",
                "Cookie": "session=abc",
                "X-API-Key": "key123",
                "X-Trace": "ok",
            },
        )

        self.assertEqual(response.status_code, 200)
        request_log_call = logger.info.call_args_list[0]
        headers = request_log_call.kwargs["headers"]
        self.assertEqual(headers["authorization"], "<redacted>")
        self.assertEqual(headers["cookie"], "<redacted>")
        self.assertEqual(headers["x-api-key"], "<redacted>")
        self.assertEqual(headers["x-trace"], "ok")

    def test_logs_username_when_authenticated(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)
        app.add_middleware(_AuthStubMiddleware)

        app.add_api_route("/ping", endpoint=lambda: {"ping": "pong"}, methods=["GET"])

        client = testclient.TestClient(app)
        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        request_log = logger.info.call_args_list[0].kwargs
        response_log = logger.info.call_args_list[1].kwargs
        self.assertEqual(request_log["username"], "alice")
        self.assertEqual(response_log["username"], "alice")


class _AuthStubMiddleware(middlewares.BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        setattr(
            request.state,
            AUTH_CTX_STATE_ATTR,
            AuthContext(user=auth.User(1, auth.Role.ADMIN, "alice"), token="token"),
        )
        return await call_next(request)
