import dataclasses
import datetime
import json
from functools import wraps
from typing import Any, Awaitable, Callable

import aiohttp_apispec
import structlog
from aiohttp import web

from app import domain
from app.lib import server as libserver
from app.lib.server import middleware
from app.presentation.server import config


def start(cfg: config.ServerConfig, actions: domain.Actions, logger: structlog.stdlib.BoundLogger):
    app = web.Application(middlewares=[middleware.exception_middleware])

    for method, path, func in config.routes:
        app.router.add_route(method, path, json_wrapper(actions, func))

    aiohttp_apispec.setup_aiohttp_apispec(
        app=app,
        title="API specification for HyperLeda",
        swagger_path=config.SWAGGER_UI_URL,
    )

    logger.info(
        "starting server",
        url=f"{cfg.host}:{cfg.port}",
        swagger_ui=f"{cfg.host}:{cfg.port}{config.SWAGGER_UI_URL}",
    )

    web.run_app(app, port=cfg.port, access_log_class=libserver.AccessLogger)


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
