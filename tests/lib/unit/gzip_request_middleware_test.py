import gzip
import http
import json

import pydantic
import pytest
import structlog
from fastapi import testclient

from app.lib.web.server.config import ServerConfig
from app.lib.web.server.server import APIOkResponse, Route, WebServer


class EchoRequest(pydantic.BaseModel):
    value: str


class EchoResponse(pydantic.BaseModel):
    echo: str


@pytest.fixture
def client() -> testclient.TestClient:
    def handler(r: EchoRequest) -> APIOkResponse[EchoResponse]:
        return APIOkResponse(data=EchoResponse(echo=r.value))

    routes = [Route(path="/echo", method=http.HTTPMethod.POST, handler=handler, summary="echo")]
    srv = WebServer(
        routes,
        ServerConfig(port=8000, host="127.0.0.1"),
        structlog.get_logger(),
        authenticator=None,
        auth_enabled=False,
    )
    return testclient.TestClient(srv.app)


def test_gzip_body_is_decompressed(client: testclient.TestClient) -> None:
    body = gzip.compress(json.dumps({"value": "hello"}).encode())

    response = client.post(
        "/api/echo",
        content=body,
        headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["echo"] == "hello"


def test_plain_body_still_works(client: testclient.TestClient) -> None:
    response = client.post("/api/echo", json={"value": "hello"})

    assert response.status_code == 200
    assert response.json()["data"]["echo"] == "hello"
