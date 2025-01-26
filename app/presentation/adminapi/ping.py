from dataclasses import dataclass

from aiohttp import web
from marshmallow import Schema, fields

from app.commands.adminapi import depot
from app.lib.web import responses, server
from app.presentation.adminapi import common


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


async def ping_handler(_: depot.Depot, __: web.Request) -> responses.APIOkResponse:
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
    return responses.APIOkResponse(PingResponse())


description = common.handler_description(
    server.HTTPMethod.GET,
    "/ping",
    ping_handler,
    PingRequestSchema,
    PingResponseSchema,
)
