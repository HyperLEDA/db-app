import dataclasses
import datetime
import json
from functools import wraps
from typing import Any, Awaitable, Callable

import aiohttp_apispec
import structlog
from aiohttp import abc, web
from marshmallow import Schema, fields, post_load

from app import domain
from app.lib.exceptions import APIException, new_internal_error
from app.presentation.server import handlers

log: structlog.stdlib.BoundLogger = structlog.get_logger()

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
    (HTTPMETHOD_GET, "/ping", handlers.ping),
    (HTTPMETHOD_POST, "/api/v1/admin/source", handlers.create_source),
    (HTTPMETHOD_GET, "/api/v1/source", handlers.get_source),
    (HTTPMETHOD_GET, "/api/v1/source/list", handlers.get_source_list),
    (HTTPMETHOD_POST, "/api/v1/admin/object/batch", handlers.create_objects),
    (HTTPMETHOD_POST, "/api/v1/admin/object", handlers.create_object),
    (HTTPMETHOD_GET, "/api/v1/object/names", handlers.get_object_names),
    (HTTPMETHOD_GET, "/api/v1/pipeline/catalogs", handlers.search_catalogs),
    (HTTPMETHOD_POST, "/api/v1/task", handlers.start_task),
    (HTTPMETHOD_POST, "/api/v1/debug/task", handlers.debug_start_task),
    (HTTPMETHOD_GET, "/api/v1/task", handlers.get_task_info),
]


def start(config: ServerConfig, actions: domain.Actions):
    app = web.Application(middlewares=[exception_middleware])

    for method, path, func in routes:
        app.router.add_route(method, path, json_wrapper(actions, func))

    aiohttp_apispec.setup_aiohttp_apispec(
        app=app,
        title="API specification for HyperLeda",
        swagger_path=SWAGGER_UI_URL,
    )

    log.info(
        "starting server",
        url=f"{config.host}:{config.port}",
        swagger_ui=f"{config.host}:{config.port}{SWAGGER_UI_URL}",
    )

    web.run_app(app, port=config.port, access_log_class=AccessLogger)


class AccessLogger(abc.AbstractAccessLogger):
    def log(self, request: web.BaseRequest, response: web.StreamResponse, time: float) -> None:
        log.info(
            "request",
            method=request.method,
            remote=request.remote,
            path=request.path,
            elapsed=f"{time:.03f}s",
            query=dict(request.query),
            response_status=response.status,
            request_content_type=request.content_type,
            response_content_type=response.content_type,
        )


@web.middleware
async def exception_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    try:
        response = await handler(request)
    except APIException as e:
        log.exception(str(e))
        response = web.json_response(e.dict(), status=e.status)
    except Exception as e:
        exc = new_internal_error(e)
        log.exception(str(exc))
        response = web.json_response(exc.dict(), status=500)

    return response


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
