import http
import unittest
from typing import cast
from unittest.mock import Mock

import pydantic
import structlog
from fastapi import testclient
from opentelemetry import trace
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.lib import auth
from app.lib.web.server.config import ServerConfig
from app.lib.web.server.server import APIOkResponse, Route, WebServer


class MockResponse(pydantic.BaseModel):
    echo: str


class TracingMiddlewareTest(unittest.TestCase):
    def setUp(self) -> None:
        exporter = InMemorySpanExporter()
        provider = sdk_trace.TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self.exporter = exporter

        self.config = ServerConfig(port=8000, host="127.0.0.1")
        self.logger = Mock(spec=structlog.stdlib.BoundLogger)

        def handler() -> APIOkResponse[MockResponse]:
            return APIOkResponse(data=MockResponse(echo="ok"))

        self.routes = [
            Route(
                path="/pub",
                method=http.HTTPMethod.GET,
                handler=handler,
                summary="public",
            ),
        ]

    def test_authenticated_request_sets_username_on_span(self) -> None:
        authenticator = _FakeAuthenticator(
            {
                "good": (auth.User(1, auth.Role.ADMIN, "alice"), True),
            }
        )
        srv = WebServer(self.routes, self.config, self.logger, authenticator, auth_enabled=True)
        client = testclient.TestClient(srv.app)

        response = client.get("/api/pub", headers={"Authorization": "Bearer good"})

        self.assertEqual(response.status_code, 200)
        spans = self.exporter.get_finished_spans()
        http_spans = [s for s in spans if s.attributes.get("http.route") == "/api/pub"]
        self.assertTrue(http_spans)
        self.assertEqual(http_spans[0].attributes.get("username"), "alice")


class _FakeAuthenticator(auth.Authenticator):
    def __init__(self, by_token: dict[str, tuple[auth.User, bool]]) -> None:
        self._by_token = by_token

    def login(self, username: str, password: str) -> tuple[str, bool]:
        return "", False

    def authenticate(self, token: str) -> tuple[auth.User, bool]:
        return cast(tuple[auth.User, bool], self._by_token.get(token, (None, False)))

    def revoke(self, token: str) -> None:
        pass
