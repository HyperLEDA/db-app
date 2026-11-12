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


def test_gzip_and_plain_bodies(client: testclient.TestClient) -> None:
    gzipped = client.post(
        "/api/echo",
        content=gzip.compress(json.dumps({"value": "hello"}).encode()),
        headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
    )
    plain = client.post("/api/echo", json={"value": "hello"})
    assert gzipped.status_code == plain.status_code == 200
    assert gzipped.json()["data"]["echo"] == plain.json()["data"]["echo"] == "hello"
