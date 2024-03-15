import dataclasses
import json
from functools import wraps
from typing import Any, Callable

from aiohttp import web
from aiohttp.web import middleware
from aiohttp_apispec import setup_aiohttp_apispec
from marshmallow import Schema, fields, post_load

from app.presentation.server import handlers
from app.presentation.server.exceptions import APIException, new_internal_error

HTTPMETHOD_GET = "GET"
HTTPMETHOD_POST = "POST"


@dataclasses.dataclass
class ServerConfig:
    port: int


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)

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
    (HTTPMETHOD_GET, "/api/v1/object", handlers.get_object),
    (HTTPMETHOD_GET, "/api/v1/object/search", handlers.search_objects),
]


def start(config: ServerConfig):
    app = web.Application(middlewares=[exception_middleware])

    for method, path, func in routes:
        app.router.add_route(method, path, json_wrapper(func))

    setup_aiohttp_apispec(app=app, title="API specification for HyperLeda", swagger_path="/api/docs")

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
