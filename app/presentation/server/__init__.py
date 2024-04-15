import dataclasses
import datetime
import json
from functools import wraps
from typing import Any, Awaitable, Callable

import aiohttp_apispec
import structlog
from aiohttp import web
from marshmallow import Schema, fields, post_load

from app import domain
from app.lib import server
from app.lib.server import middleware
from app.presentation.server import handlers

HTTPMETHOD_GET = "GET"
HTTPMETHOD_POST = "POST"

SWAGGER_UI_URL = "/api/docs"


@dataclasses.dataclass
class ServerConfig:
    port: int
    host: str


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)
    host = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)


routes = [
    (HTTPMETHOD_GET, "/ping", handlers.ping_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/source", handlers.create_source_handler),
    (HTTPMETHOD_GET, "/api/v1/source", handlers.get_source_handler),
    (HTTPMETHOD_GET, "/api/v1/source/list", handlers.get_source_list_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/object/batch", handlers.create_objects_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/object", handlers.create_object_handler),
    (HTTPMETHOD_GET, "/api/v1/object/names", handlers.get_object_names_handler),
    (HTTPMETHOD_GET, "/api/v1/pipeline/catalogs", handlers.search_catalogs_handler),
    (HTTPMETHOD_POST, "/api/v1/task", handlers.start_task_handler),
    (HTTPMETHOD_POST, "/api/v1/debug/task", handlers.debug_start_task_handler),
    (HTTPMETHOD_GET, "/api/v1/task", handlers.get_task_info_handler),
]


def start(config: ServerConfig, actions: domain.Actions, logger: structlog.stdlib.BoundLogger):
    app = web.Application(middlewares=[middleware.exception_middleware])

    for method, path, func in routes:
        app.router.add_route(method, path, json_wrapper(actions, func))

    aiohttp_apispec.setup_aiohttp_apispec(
        app=app,
        title="API specification for HyperLeda",
        swagger_path=SWAGGER_UI_URL,
    )

    logger.info(
        "starting server",
        url=f"{config.host}:{config.port}",
        swagger_ui=f"{config.host}:{config.port}{SWAGGER_UI_URL}",
    )

    web.run_app(app, port=config.port, access_log_class=server.AccessLogger)


def datetime_handler(obj: Any):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

    raise TypeError("Unknown type")


def custom_dumps(obj):
    return json.dumps(obj, default=datetime_handler)


def json_wrapper(
    actions: domain.Actions, func: Callable[[domain.Actions, web.Request], Any]
) -> Callable[[web.Request], Awaitable[web.Response]]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(actions, request)
        return web.json_response({"data": dataclasses.asdict(response)}, dumps=custom_dumps)

    return inner
