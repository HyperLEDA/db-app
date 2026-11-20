from collections.abc import Awaitable, Callable
from unittest import mock

import fastapi
import structlog
from fastapi import testclient
from starlette.middleware import base as middlewares

from app.lib.web.middlewares.auth import AUTH_CTX_STATE_ATTR, AuthContext
from app.lib.web.middlewares.log import LoggingMiddleware


def _client(
    logger: mock.Mock,
    *,
    handler: Callable[..., object] | None = None,
    auth: bool = False,
    log_bodies: set[tuple[str, str]] | None = None,
    extra_routes: list[tuple[str, str, Callable[..., object]]] | None = None,
) -> testclient.TestClient:
    app = fastapi.FastAPI()
    app.add_middleware(LoggingMiddleware, logger=logger, **({"log_bodies": log_bodies} if log_bodies else {}))
    if auth:
        app.add_middleware(_AuthStubMiddleware)
    app.add_api_route("/echo", endpoint=handler or (lambda: {"ok": True}), methods=["GET"])
    for path, method, endpoint in extra_routes or []:
        app.add_api_route(path, endpoint=endpoint, methods=[method.upper()])
    return testclient.TestClient(app)


def test_request_headers_are_redacted() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    response = _client(logger).get(
        "/echo",
        headers={"Authorization": "Bearer secret", "Cookie": "session=abc", "X-API-Key": "key123", "X-Trace": "ok"},
    )
    assert response.status_code == 200
    headers = logger.info.call_args_list[0].kwargs["headers"]
    assert headers["authorization"] == headers["cookie"] == headers["x-api-key"] == "<redacted>"
    assert headers["x-trace"] == "ok"


def test_logs_username_when_authenticated() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    assert _client(logger, auth=True).get("/echo").status_code == 200
    assert (
        logger.info.call_args_list[0].kwargs["username"] == logger.info.call_args_list[1].kwargs["username"] == "alice"
    )


def test_binds_request_id_for_handler() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    seen: dict[str, str] = {}

    def handler() -> dict[str, str]:
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        assert isinstance(request_id, str)
        seen["request_id"] = request_id
        return {"ok": "true"}

    assert _client(logger, handler=handler).get("/echo").status_code == 200
    assert seen["request_id"]
    assert structlog.contextvars.get_contextvars() == {}


def test_request_id_differs_across_requests() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    seen: list[str] = []

    def handler() -> dict[str, str]:
        request_id = structlog.contextvars.get_contextvars()["request_id"]
        assert isinstance(request_id, str)
        seen.append(request_id)
        return {"ok": "true"}

    client = _client(logger, handler=handler)
    assert client.get("/echo").status_code == client.get("/echo").status_code == 200
    assert len(seen) == 2 and seen[0] != seen[1]


def test_logs_client_ip_from_x_forwarded_for() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    seen: dict[str, str] = {}

    def handler() -> dict[str, str]:
        client_ip = structlog.contextvars.get_contextvars().get("client_ip")
        assert isinstance(client_ip, str)
        seen["client_ip"] = client_ip
        return {"ok": "true"}

    response = _client(logger, handler=handler).get("/echo", headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.1"})
    assert response.status_code == 200
    assert seen["client_ip"] == "203.0.113.10"
    assert (
        logger.info.call_args_list[0].kwargs["client_ip"]
        == logger.info.call_args_list[1].kwargs["client_ip"]
        == "203.0.113.10"
    )


def test_logs_client_ip_from_x_real_ip() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    response = _client(logger).get("/echo", headers={"X-Real-IP": "198.51.100.7"})
    assert response.status_code == 200
    assert logger.info.call_args_list[0].kwargs["client_ip"] == "198.51.100.7"


def test_logs_request_body_only_for_configured_routes() -> None:
    logger = mock.Mock(spec=structlog.stdlib.BoundLogger)
    client = _client(
        logger,
        log_bodies={("/admin/api/v1/source", "post")},
        extra_routes=[
            ("/admin/api/v1/ping-body", "post", lambda: {"ok": True}),
            ("/admin/api/v1/source", "post", lambda: {"ok": True}),
        ],
    )
    assert client.post("/admin/api/v1/ping-body", json={"username": "alice", "password": "secret"}).status_code == 200
    assert client.post("/admin/api/v1/source", json={"title": "t"}).status_code == 200
    assert "body" not in logger.info.call_args_list[0].kwargs
    assert "body" in logger.info.call_args_list[2].kwargs


class _AuthStubMiddleware(middlewares.BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        setattr(request.state, AUTH_CTX_STATE_ATTR, AuthContext(login="alice"))
        return await call_next(request)
