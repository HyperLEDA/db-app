import dataclasses
import datetime
import enum
import json
from collections.abc import Awaitable
from functools import wraps
from typing import Any, Callable, final

from aiohttp import typedefs as httptypes
from aiohttp import web
from marshmallow.schema import Schema

from app import commands
from app.lib.web import responses, server


class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    # add more if needed


def datetime_handler(obj: Any):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    if isinstance(obj, enum.Enum):
        return obj.value

    raise TypeError("Unknown type")


def custom_dumps(obj):
    return json.dumps(obj, default=datetime_handler)


def json_wrapper(
    depot: commands.Depot, func: Callable[[commands.Depot, web.Request], responses.APIOkResponse]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(depot, request)

        return web.json_response(
            {"data": dataclasses.asdict(response.data)},
            dumps=custom_dumps,
            status=response.status,
        )

    return inner


def handler_description(
    method: HTTPMethod,
    endpoint: str,
    handler: Callable[[commands.Depot, web.Request], Awaitable[responses.APIOkResponse]],
    request_type: type,
    response_type: type,
    summary: str,
    description: str,
) -> Callable[[commands.Depot], server.Route]:
    def wrapper(depot: commands.Depot) -> server.Route:
        return HandlerDescription(
            depot,
            method,
            endpoint,
            handler,
            request_type,
            response_type,
            summary,
            description,
        )

    return wrapper


@dataclasses.dataclass
@final
class HandlerDescription(server.Route):
    depot: commands.Depot
    http_method: HTTPMethod
    endpoint: str
    action: Callable[[commands.Depot, web.Request], responses.APIOkResponse]
    request_type: type
    response_type: type
    summary: str
    description: str

    def request_schema(self) -> type[Schema]:
        return self.request_type

    def response_schema(self) -> type[Schema]:
        return self.response_type

    def method(self) -> str:
        return self.http_method.value

    def path(self) -> str:
        return self.endpoint

    def handler(self) -> httptypes.Handler:
        return json_wrapper(self.depot, self.action)

    def spec(self) -> dict:
        return {
            "summary": self.summary,
            "description": self.description,
        }
