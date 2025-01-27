import dataclasses
import datetime
import enum
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from aiohttp import web

from app.lib.web import responses, server
from app.presentation.adminapi import (
    add_data,
    create_source,
    create_table,
    get_source,
    get_task_info,
    interface,
    login,
    set_table_status,
    start_task,
    table_process,
    table_status_stats,
)


def datetime_handler(obj: Any):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    if isinstance(obj, enum.Enum):
        return obj.value

    raise TypeError("Unknown type")


def custom_dumps(obj):
    return json.dumps(obj, default=datetime_handler)


def json_wrapper(
    d: interface.Actions, func: Callable[[interface.Actions, web.Request], Awaitable[responses.APIOkResponse]]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(d, request)

        return web.json_response(
            {"data": dataclasses.asdict(response.data)},
            dumps=custom_dumps,
            status=response.status,
        )

    return inner


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
        super().__init__(self.routes(actions), config, *args, **kwargs)

    @classmethod
    def routes(cls, actions: interface.Actions) -> list[server.Route]:
        return [
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/table/data",
                    add_data.AddDataRequestSchema,
                    add_data.AddDataResponseSchema,
                ),
                add_data.add_data_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/source",
                    create_source.CreateSourceRequestSchema,
                    create_source.CreateSourceResponseSchema,
                ),
                create_source.create_source_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/table",
                    create_table.CreateTableRequestSchema,
                    create_table.CreateTableResponseSchema,
                ),
                create_table.create_table_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.GET,
                    "/api/v1/source",
                    get_source.GetSourceRequestSchema,
                    get_source.GetSourceResponseSchema,
                ),
                get_source.get_source_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.GET,
                    "/api/v1/admin/task",
                    get_task_info.GetTaskInfoRequestSchema,
                    get_task_info.GetTaskInfoResponseSchema,
                ),
                get_task_info.get_task_info_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/login",
                    login.LoginRequestSchema,
                    login.LoginResponseSchema,
                ),
                login.login_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/table/status",
                    set_table_status.SetTableStatusRequestSchema,
                    set_table_status.SetTableStatusResponseSchema,
                ),
                set_table_status.set_table_status_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/task",
                    start_task.StartTaskRequestSchema,
                    start_task.StartTaskResponseSchema,
                ),
                start_task.start_task_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.POST,
                    "/api/v1/admin/table/process",
                    table_process.TableProcessRequestSchema,
                    table_process.TableProcessResponseSchema,
                ),
                table_process.table_process_handler,
            ),
            Route(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.GET,
                    "/api/v1/table/status/stats",
                    table_status_stats.TableStatusStatsRequestSchema,
                    table_status_stats.TableStatusStatsResponseSchema,
                ),
                table_status_stats.table_status_stats,
            ),
        ]
