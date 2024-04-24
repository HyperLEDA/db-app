import dataclasses
import datetime
import json
import warnings
from functools import wraps
from typing import Any, Awaitable, Callable

import apispec
import apispec.exceptions
import structlog
import swagger_ui
from aiohttp import web
from apispec.ext import marshmallow as apimarshamllow
from apispec_webframeworks import aiohttp as apiaiohttp

from app import domain
from app.lib import server as libserver
from app.lib.server import middleware
from app.presentation.server import config


def start(cfg: config.ServerConfig, actions: domain.Actions, logger: structlog.stdlib.BoundLogger):
    # silence warning from apispec since it is a desired behaviour in this case.
    warnings.filterwarnings("ignore", message="(.*?)has already been added to the spec(.*?)", module="apispec")

    app = web.Application(middlewares=[middleware.exception_middleware])

    spec = apispec.APISpec(
        title="HyperLeda API specification",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[apimarshamllow.MarshmallowPlugin(), apiaiohttp.AiohttpPlugin()],
    )

    for method, path, description in config.routes:
        route = app.router.add_route(method, path, json_wrapper(actions, description.handler))

        if description.request_schema.__name__ not in spec.components.schemas:
            spec.components.schema(description.request_schema.__name__, schema=description.request_schema)
        if description.response_schema.__name__ not in spec.components.schemas:
            spec.components.schema(description.response_schema.__name__, schema=description.response_schema)

        spec.path(route=route)

    swagger_ui.api_doc(
        app,
        config=spec.to_dict(),
        url_prefix=config.SWAGGER_UI_URL,
        title="HyperLeda API",
        parameters={
            "tryItOutEnabled": "true",
            "filter": "true",
            "displayRequestDuration": "true",
            "showCommonExtensions": "true",
            "requestSnippetsEnabled": "true",
            "persistAuthorization": "true",
        },
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
