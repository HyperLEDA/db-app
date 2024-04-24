from dataclasses import dataclass
from typing import Any

from aiohttp import web
from marshmallow import Schema

from app import domain
from app.presentation.server.handlers import common


@dataclass
class PingRequest:
    pass


class PingRequestSchema(Schema):
    pass


@dataclass
class PingResponse:
    ping: str = "pong"


class PingResponseSchema(Schema):
    pass


async def ping_handler(_: domain.Actions, __: web.Request) -> Any:
    """---
    summary: Test that service is up and running
    tags: [admin]
    responses:
        200:
            description: Source was successfully obtained
            content:
                application/json:
                    schema: PingResponseSchema
    """
    return PingResponse()


description = common.HandlerDescription(
    common.HTTPMethod.GET,
    "/ping",
    ping_handler,
    PingRequestSchema,
    PingResponseSchema,
)
