import dataclasses
import json
from functools import wraps
from typing import Any, Callable

from aiohttp import web
from aiohttp.web import middleware
from aiohttp_apispec import setup_aiohttp_apispec
import aiohttp_swagger
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


def start(config: ServerConfig):
    app = web.Application(middlewares=[exception_middleware])
    app.router.add_route("GET", "/ping", json_wrapper(handlers.ping))
    app.router.add_route("POST", "/api/v1/admin/source", json_wrapper(handlers.create_source))
    setup_aiohttp_apispec(app=app, title="Swagger UI", version="v1")
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
