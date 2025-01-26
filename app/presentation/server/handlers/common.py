import dataclasses
import datetime
import enum
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from aiohttp import typedefs as httptypes
from aiohttp import web
from marshmallow.schema import Schema

from app import commands
from app.lib.web import responses, server


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
    method: server.HTTPMethod,
    endpoint: str,
    handler: Callable[[commands.Depot, web.Request], Awaitable[responses.APIOkResponse]],
    request_type: type,
    response_type: type,
) -> Callable[[commands.Depot], server.Route]:
    def wrapper(depot: commands.Depot) -> server.Route:
        return HandlerDescription(depot, handler, server.RouteInfo(method, endpoint, request_type, response_type))

    return wrapper


@dataclasses.dataclass
class HandlerDescription(server.Route):
    depot: commands.Depot
    action: Callable[[commands.Depot, web.Request], responses.APIOkResponse]
    route_info: server.RouteInfo

    def request_schema(self) -> type[Schema]:
        return self.route_info.request_schema

    def response_schema(self) -> type[Schema]:
        return self.route_info.response_schema

    def method(self) -> str:
        return self.route_info.method.value

    def path(self) -> str:
        return self.route_info.endpoint

    def handler(self) -> httptypes.Handler:
        return json_wrapper(self.depot, self.action)
