import http
import unittest
from unittest.mock import Mock

import pydantic
import structlog
from fastapi import testclient

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
        server = WebServer(self.routes, self.config, self.logger)
        client = testclient.TestClient(server.app)

        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"ping": "pong"}})

    def test_custom_endpoint(self):
        server = WebServer(self.routes, self.config, self.logger)
        client = testclient.TestClient(server.app)

        test_data = {"message": "Hello, World!"}
        response = client.post("/api/test", json=test_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": {"echo": "Hello, World!"}})

    def test_custom_endpoint_validation_error(self):
        server = WebServer(self.routes, self.config, self.logger)
        client = testclient.TestClient(server.app)

        invalid_data = {"invalid_field": "value"}
        response = client.post("/api/test", json=invalid_data)

        self.assertEqual(response.status_code, 400)
