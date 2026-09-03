import http
from typing import cast

import pydantic
import pytest
import structlog
from fastapi import testclient

from app.lib import auth, mock
from app.lib.web.server.config import ServerConfig
from app.lib.web.server.server import APIOkResponse, Route, WebServer


class MockRequest(pydantic.BaseModel):
    message: str


class MockResponse(pydantic.BaseModel):
    echo: str


@pytest.fixture
def config() -> ServerConfig:
    return ServerConfig(port=8000, host="127.0.0.1")


@pytest.fixture
def logger() -> mock.Mock:
    return mock.Mock(spec=structlog.stdlib.BoundLogger)


@pytest.fixture
def test_route() -> Route:
    def test_handler(request: MockRequest) -> APIOkResponse[MockResponse]:
        return APIOkResponse(data=MockResponse(echo=request.message))

    return Route(
        path="/test",
        method=http.HTTPMethod.POST,
        handler=test_handler,
        summary="Test endpoint",
    )


@pytest.fixture
def routes(test_route: Route) -> list[Route]:
    return [test_route]


def test_ping_endpoint(config: ServerConfig, logger: mock.Mock, routes: list[Route]) -> None:
    server = WebServer(routes, config, logger, auth.NoopAuthenticator())
    client = testclient.TestClient(server.app)

    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"data": {"ping": "pong"}}


def test_custom_endpoint(config: ServerConfig, logger: mock.Mock, routes: list[Route]) -> None:
    server = WebServer(routes, config, logger, auth.NoopAuthenticator())
    client = testclient.TestClient(server.app)

    test_data = {"message": "Hello, World!"}
    response = client.post("/api/test", json=test_data)

    assert response.status_code == 200
    assert response.json() == {"data": {"echo": "Hello, World!"}}


def test_custom_endpoint_validation_error(config: ServerConfig, logger: mock.Mock, routes: list[Route]) -> None:
    server = WebServer(routes, config, logger, auth.NoopAuthenticator())
    client = testclient.TestClient(server.app)

    invalid_data = {"invalid_field": "value"}
    response = client.post("/api/test", json=invalid_data)

    assert response.status_code == 400


class _FakeAuthenticator(auth.Authenticator):
    def __init__(self, by_token: dict[str, tuple[auth.User, bool]]) -> None:
        self._by_token = by_token

    def login(self, username: str, password: str) -> tuple[str, bool]:
        return "", False

    def authenticate(self, token: str) -> tuple[auth.User, bool]:
        return cast(tuple[auth.User, bool], self._by_token.get(token, (None, False)))

    def revoke(self, token: str) -> None:
        pass


@pytest.fixture
def auth_routes() -> list[Route]:
    def public_get() -> APIOkResponse[MockResponse]:
        return APIOkResponse(data=MockResponse(echo="public"))

    def secured_post(request: MockRequest) -> APIOkResponse[MockResponse]:
        return APIOkResponse(data=MockResponse(echo=request.message))

    return [
        Route(
            path="/pub",
            method=http.HTTPMethod.GET,
            handler=public_get,
            summary="public",
        ),
        Route(
            path="/sec",
            method=http.HTTPMethod.POST,
            handler=secured_post,
            summary="secured",
            allowed_roles=[auth.Role.ADMIN],
        ),
        Route(
            path="/closed",
            method=http.HTTPMethod.POST,
            handler=secured_post,
            summary="closed",
            allowed_roles=[],
        ),
    ]


def test_public_and_role_gates(
    config: ServerConfig,
    logger: mock.Mock,
    auth_routes: list[Route],
) -> None:
    authenticator = _FakeAuthenticator(
        {
            "good": (auth.User(1, auth.Role.ADMIN, "admin"), True),
        }
    )
    srv = WebServer(auth_routes, config, logger, authenticator, auth_enabled=True)
    client = testclient.TestClient(srv.app)

    assert client.get("/api/pub").status_code == 200

    assert client.post("/api/sec", json={"message": "x"}).status_code == 401
    assert client.post("/api/sec", json={"message": "x"}).json()["message"] == "No authorization header"
    bad_scheme = client.post(
        "/api/sec",
        json={"message": "x"},
        headers={"Authorization": "Basic abc"},
    )
    assert bad_scheme.status_code == 401
    assert bad_scheme.json()["message"] == "Invalid authorization header"
    assert client.post("/api/sec", json={"message": "x"}, headers={"Authorization": "Bearer good"}).status_code == 200
    invalid = client.post(
        "/api/sec",
        json={"message": "x"},
        headers={"Authorization": "Bearer invalid"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["message"] == "Invalid token"

    assert (
        client.post("/api/closed", json={"message": "x"}, headers={"Authorization": "Bearer good"}).status_code == 403
    )


def test_auth_disabled_skips_middleware_gate(
    config: ServerConfig,
    logger: mock.Mock,
    auth_routes: list[Route],
) -> None:
    authenticator = _FakeAuthenticator({})
    srv = WebServer(auth_routes, config, logger, authenticator, auth_enabled=False)
    client = testclient.TestClient(srv.app)

    assert client.post("/api/sec", json={"message": "x"}).status_code == 200
