import http
import unittest
from typing import cast
from unittest.mock import Mock

import pydantic
import structlog
from fastapi import testclient

from app.lib import auth
from app.lib.web.server.config import ServerConfig
from app.lib.web.server.server import APIOkResponse, Route, WebServer


class MockRequest(pydantic.BaseModel):
    message: str


class MockResponse(pydantic.BaseModel):
    echo: str


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.config = ServerConfig(port=8000, host="127.0.0.1")
        self.logger = Mock(spec=structlog.stdlib.BoundLogger)

        def test_handler(request: MockRequest) -> APIOkResponse[MockResponse]:
            return APIOkResponse(data=MockResponse(echo=request.message))

        self.test_route = Route(
            path="/test",
            method=http.HTTPMethod.POST,
            handler=test_handler,
            summary="Test endpoint",
        )

        self.routes = [self.test_route]

    def test_ping_endpoint(self):
        server = WebServer(self.routes, self.config, self.logger, auth.NoopAuthenticator())
        client = testclient.TestClient(server.app)

        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"ping": "pong"}})

    def test_custom_endpoint(self):
        server = WebServer(self.routes, self.config, self.logger, auth.NoopAuthenticator())
        client = testclient.TestClient(server.app)

        test_data = {"message": "Hello, World!"}
        response = client.post("/api/test", json=test_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"echo": "Hello, World!"}})

    def test_custom_endpoint_validation_error(self):
        server = WebServer(self.routes, self.config, self.logger, auth.NoopAuthenticator())
        client = testclient.TestClient(server.app)

        invalid_data = {"invalid_field": "value"}
        response = client.post("/api/test", json=invalid_data)

        self.assertEqual(response.status_code, 400)


class _FakeAuthenticator(auth.Authenticator):
    def __init__(self, by_token: dict[str, tuple[auth.User, bool]]) -> None:
        self._by_token = by_token

    def login(self, username: str, password: str) -> tuple[str, bool]:
        return "", False

    def authenticate(self, token: str) -> tuple[auth.User, bool]:
        return cast(tuple[auth.User, bool], self._by_token.get(token, (None, False)))

    def revoke(self, token: str) -> None:
        pass


class ServerRouteAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ServerConfig(port=8000, host="127.0.0.1")
        self.logger = Mock(spec=structlog.stdlib.BoundLogger)

        def public_get() -> APIOkResponse[MockResponse]:
            return APIOkResponse(data=MockResponse(echo="public"))

        def secured_post(request: MockRequest) -> APIOkResponse[MockResponse]:
            return APIOkResponse(data=MockResponse(echo=request.message))

        self.routes = [
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

    def test_public_and_role_gates(self) -> None:
        authenticator = _FakeAuthenticator(
            {
                "good": (auth.User(1, auth.Role.ADMIN), True),
            }
        )
        srv = WebServer(self.routes, self.config, self.logger, authenticator, enforce_route_auth=True)
        client = testclient.TestClient(srv.app)

        self.assertEqual(client.get("/api/pub").status_code, 200)

        self.assertEqual(client.post("/api/sec", json={"message": "x"}).status_code, 401)
        self.assertEqual(
            client.post("/api/sec", json={"message": "x"}, headers={"Authorization": "Bearer good"}).status_code,
            200,
        )
        self.assertEqual(
            client.post("/api/sec", json={"message": "x"}, headers={"Authorization": "Bearer invalid"}).status_code,
            401,
        )

        self.assertEqual(
            client.post("/api/closed", json={"message": "x"}, headers={"Authorization": "Bearer good"}).status_code,
            403,
        )

    def test_enforce_route_auth_false_skips_dependencies(self) -> None:
        authenticator = _FakeAuthenticator({})
        srv = WebServer(self.routes, self.config, self.logger, authenticator, enforce_route_auth=False)
        client = testclient.TestClient(srv.app)

        self.assertEqual(client.post("/api/sec", json={"message": "x"}).status_code, 200)
