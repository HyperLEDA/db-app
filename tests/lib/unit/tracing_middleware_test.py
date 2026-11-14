import http
from unittest import mock

import pydantic
import pytest
import structlog
from fastapi import testclient
from opentelemetry import trace
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.lib.web.server.config import ServerConfig
from app.lib.web.server.server import APIOkResponse, Route, WebServer


class MockResponse(pydantic.BaseModel):
    echo: str


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = sdk_trace.TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture
def config() -> ServerConfig:
    return ServerConfig(port=8000, host="127.0.0.1")


@pytest.fixture
def logger() -> mock.Mock:
    return mock.Mock(spec=structlog.stdlib.BoundLogger)


@pytest.fixture
def routes() -> list[Route]:
    def handler() -> APIOkResponse[MockResponse]:
        return APIOkResponse(data=MockResponse(echo="ok"))

    return [
        Route(
            path="/pub",
            method=http.HTTPMethod.GET,
            handler=handler,
            summary="public",
            requires_auth=True,
        ),
    ]


def test_authenticated_request_sets_username_on_span(
    span_exporter: InMemorySpanExporter,
    config: ServerConfig,
    logger: mock.Mock,
    routes: list[Route],
) -> None:
    srv = WebServer(routes, config, logger, auth_enabled=True)
    client = testclient.TestClient(srv.app)

    response = client.get("/api/pub", headers={"Remote-User": "alice"})

    assert response.status_code == 200
    spans = span_exporter.get_finished_spans()
    http_spans = [s for s in spans if s.attributes.get("http.route") == "/api/pub"]
    assert http_spans
    assert http_spans[0].attributes.get("username") == "alice"
