from dataclasses import dataclass
from typing import Any

from aiohttp import web
from marshmallow import Schema, fields

from app import commands
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
    ping = fields.Str(example="pong")


async def ping_handler(_: commands.Depot, __: web.Request) -> Any:
    """---
    summary: Test that service is up and running
    tags: [admin]
    responses:
        200:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: PingResponseSchema
    """
    return PingResponse()


description = common.HandlerDescription(
    common.HTTPMethod.GET,
    "/ping",
    ping_handler,
    PingRequestSchema,
    PingResponseSchema,
)
