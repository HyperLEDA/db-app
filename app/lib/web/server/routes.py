import abc
import dataclasses
import datetime
import enum
import http
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

import aiohttp
import aiohttp.typedefs
import marshmallow
from aiohttp import web

from app.lib.web import responses


class Route(abc.ABC):
    @abc.abstractmethod
    def request_schema(self) -> type[marshmallow.Schema]:
        """
        Returns schema for the request.
        """

    @abc.abstractmethod
    def response_schema(self) -> type[marshmallow.Schema]:
        """
        Returns schema for the response.
        """

    @abc.abstractmethod
    def method(self) -> str:
        """
        Returns HTTP method of the route.
        """

    @abc.abstractmethod
    def path(self) -> str:
        """
        Returns path of the route.
        """

    @abc.abstractmethod
    def handler(self) -> aiohttp.typedefs.Handler:
        """
        Returns handler of the route.
        """


@dataclass
class RouteInfo:
    method: http.HTTPMethod
    endpoint: str
    request_schema: type[marshmallow.Schema]
    response_schema: type[marshmallow.Schema] | None


def datetime_handler(obj: Any):
    # может быть тут переименовать не datetime, a просто datatype_handler или что то еще? я так поняла json все,
    # что сам не обрабатывает, сюда отправляет, в том числе юниты астропай и тд...
    # мне пришлось поразбираться, причем здесь вообще DATETIME, если у меня вообще и не date, и не time ахаха
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    if isinstance(obj, enum.Enum):
        return obj.value

    if hasattr(obj, "physical_type"):  # для astropy.units
        return str(obj)

    # print(f"UNHANDLED: {type(obj)} ---- VALUE: {obj}")
    raise TypeError("Unknown type")


def custom_dumps(obj):
    return json.dumps(obj, default=datetime_handler)


class ActionRoute[Actions](Route):
    def __init__(
        self,
        actions: Actions,
        info: RouteInfo,
        func: Callable[[Actions, web.Request], Awaitable[responses.APIOkResponse | responses.BinaryResponse]],
    ) -> None:
        self.actions = actions
        self.info = info
        self.func = func

    def request_schema(self) -> type[marshmallow.Schema]:
        return self.info.request_schema

    def response_schema(self) -> type[marshmallow.Schema]:
        return self.info.response_schema or marshmallow.Schema

    def method(self) -> str:
        return self.info.method.value

    def path(self) -> str:
        return self.info.endpoint

    def handler(self) -> aiohttp.typedefs.Handler:
        @wraps(self.func)
        async def inner(request: web.Request) -> web.Response:
            response = await self.func(self.actions, request)

            if isinstance(response, responses.BinaryResponse):
                return web.Response(
                    body=response.data,
                    content_type=response.content_type,
                    status=response.status,
                    headers=response.headers,
                )

            return web.json_response(
                {"data": dataclasses.asdict(response.data)},
                dumps=custom_dumps,
                status=response.status,
            )

        return inner
