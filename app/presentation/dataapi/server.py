import dataclasses
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import final

from aiohttp import web

from app.lib.web import responses, server
from app.presentation.dataapi import interface, query_simple


def json_wrapper(
    d: interface.Actions, func: Callable[[interface.Actions, web.Request], Awaitable[responses.APIOkResponse]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(d, request)

        return web.json_response(
            {"data": dataclasses.asdict(response.data)},
            status=response.status,
        )

    return inner


@final
class Route(server.Route):
    def __init__(
        self,
        actions: interface.Actions,
        info: server.RouteInfo,
        func: Callable[[interface.Actions, web.Request], Awaitable[responses.APIOkResponse]],
    ) -> None:
        self.actions = actions
        self.info = info
        self.func = func

    def request_schema(self):
        return self.info.request_schema

    def response_schema(self):
        return self.info.response_schema

    def method(self):
        return self.info.method.value

    def path(self):
        return self.info.endpoint

    def handler(self):
        return json_wrapper(self.actions, self.func)


class Server(server.WebServer):
    def __init__(self, actions: interface.Actions, config: server.ServerConfig, *args, **kwargs):
        self.actions = actions

        routes: list[server.Route] = [
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.GET,
                    "/api/v1/query/simple",
                    query_simple.QuerySimpleRequestSchema,
                    query_simple.QuerySimpleResponseSchema,
                ),
                query_simple.query_simple_handler,
            ),
        ]

        super().__init__(routes, config, *args, **kwargs)
