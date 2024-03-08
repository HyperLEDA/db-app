import dataclasses
import json
from functools import wraps
from http import HTTPMethod
from typing import Any, Callable

import aiohttp_swagger
from aiohttp import web
from aiohttp.web import middleware
from aiohttp_apispec import setup_aiohttp_apispec
from marshmallow import Schema, fields, post_load

from app.server import handlers
from app.server.exceptions import APIException, new_internal_error


@dataclasses.dataclass
class ServerConfig:
    port: int


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)


routes = [
    (HTTPMethod.GET, "/ping", handlers.ping),
    (HTTPMethod.POST, "/api/v1/admin/source", handlers.create_source),
    (HTTPMethod.GET, "/api/v1/source", handlers.get_source),
    (HTTPMethod.GET, "/api/v1/source/list", handlers.get_source_list),
    (HTTPMethod.POST, "/api/v1/admin/object/batch", handlers.create_objects),
    (HTTPMethod.POST, "/api/v1/admin/object", handlers.create_object),
    (HTTPMethod.GET, "/api/v1/object", handlers.get_object),
    (HTTPMethod.GET, "/api/v1/object/search", handlers.search_objects),
]


def start(config: ServerConfig):
    app = web.Application(middlewares=[exception_middleware])

    for method, path, func in routes:
        app.router.add_route(method, path, json_wrapper(func))

    setup_aiohttp_apispec(app=app, title="API specification for HyperLeda", version="v1")
    aiohttp_swagger.setup_swagger(app, swagger_url="/api/docs", ui_version=3)

    web.run_app(app, port=config.port)


@middleware
async def exception_middleware(request: web.Request, handler: Callable[[web.Request], web.Response]):
    try:
        response = await handler(request)
    except APIException as e:
        response = web.Response(text=json.dumps(dataclasses.asdict(e)))
    except Exception as e:
        response = web.Response(text=json.dumps(dataclasses.asdict(new_internal_error(e))))

    return response


def json_wrapper(func: Callable[[web.Request], dict[str, Any]]) -> Callable[[web.Request], web.Response]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(request)
        return web.json_response(response)

    return inner
