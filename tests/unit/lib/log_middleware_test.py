import unittest
from unittest import mock

import fastapi
import structlog
from fastapi import testclient

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
