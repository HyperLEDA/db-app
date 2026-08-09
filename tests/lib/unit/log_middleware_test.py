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

    def test_binds_request_id_for_handler(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)
        seen: dict[str, str] = {}

        def handler() -> dict[str, str]:
            ctx = structlog.contextvars.get_contextvars()
            request_id = ctx.get("request_id")
            assert isinstance(request_id, str)
            seen["request_id"] = request_id
            return {"ping": "pong"}

        app.add_api_route("/ping", endpoint=handler, methods=["GET"])

        client = testclient.TestClient(app)
        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        self.assertIn("request_id", seen)
        self.assertTrue(seen["request_id"])
        self.assertEqual(structlog.contextvars.get_contextvars(), {})

    def test_request_id_differs_across_requests(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)
        seen: list[str] = []

        def handler() -> dict[str, str]:
            request_id = structlog.contextvars.get_contextvars()["request_id"]
            assert isinstance(request_id, str)
            seen.append(request_id)
            return {"ping": "pong"}

        app.add_api_route("/ping", endpoint=handler, methods=["GET"])

        client = testclient.TestClient(app)
        self.assertEqual(client.get("/ping").status_code, 200)
        self.assertEqual(client.get("/ping").status_code, 200)

        self.assertEqual(len(seen), 2)
        self.assertNotEqual(seen[0], seen[1])

    def test_logs_client_ip_from_x_forwarded_for(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)
        seen: dict[str, str] = {}

        def handler() -> dict[str, str]:
            client_ip = structlog.contextvars.get_contextvars().get("client_ip")
            assert isinstance(client_ip, str)
            seen["client_ip"] = client_ip
            return {"ping": "pong"}

        app.add_api_route("/ping", endpoint=handler, methods=["GET"])

        client = testclient.TestClient(app)
        response = client.get("/ping", headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen["client_ip"], "203.0.113.10")
        request_log = logger.info.call_args_list[0].kwargs
        response_log = logger.info.call_args_list[1].kwargs
        self.assertEqual(request_log["client_ip"], "203.0.113.10")
        self.assertEqual(response_log["client_ip"], "203.0.113.10")

    def test_logs_client_ip_from_x_real_ip(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(LoggingMiddleware, logger=logger)

        app.add_api_route("/ping", endpoint=lambda: {"ping": "pong"}, methods=["GET"])

        client = testclient.TestClient(app)
        response = client.get("/ping", headers={"X-Real-IP": "198.51.100.7"})

        self.assertEqual(response.status_code, 200)
        request_log = logger.info.call_args_list[0].kwargs
        self.assertEqual(request_log["client_ip"], "198.51.100.7")

    def test_logs_request_body_only_for_configured_routes(self) -> None:
        logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
        app = fastapi.FastAPI()
        app.add_middleware(
            LoggingMiddleware,
            logger=logger,
            log_bodies={("/admin/api/v1/source", "post")},
        )

        app.add_api_route("/admin/api/v1/login", endpoint=lambda: {"ok": True}, methods=["POST"])
        app.add_api_route("/admin/api/v1/source", endpoint=lambda: {"ok": True}, methods=["POST"])

        client = testclient.TestClient(app)
        login_response = client.post(
            "/admin/api/v1/login",
            json={"username": "alice", "password": "secret"},
        )
        source_response = client.post(
            "/admin/api/v1/source",
            json={"title": "t"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(source_response.status_code, 200)
        login_log = logger.info.call_args_list[0].kwargs
        source_log = logger.info.call_args_list[2].kwargs
        self.assertNotIn("body", login_log)
        self.assertIn("body", source_log)


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
