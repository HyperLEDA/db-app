import warnings

import apispec
import apispec.exceptions
import structlog
import swagger_ui
from aiohttp import typedefs as httptypes
from aiohttp import web
from apispec.ext import marshmallow as apimarshmallow
from apispec_webframeworks import aiohttp as apiaiohttp

from app.lib import server
from app.lib.server import config, routes

log = structlog.get_logger()


class WebServer:
    def __init__(
        self,
        routes: list[routes.Route],
        *,
        middlewares: list[httptypes.Middleware] | None = None,
    ) -> None:
        default_middlewares = [
            server.exception_middleware,
        ]

        middlewares = middlewares or []
        middlewares.extend(default_middlewares)

        # silence warning from apispec since it is a desired behaviour in this case.
        warnings.filterwarnings("ignore", message="(.*?)has already been added to the spec(.*?)", module="apispec")

        app = web.Application(middlewares=middlewares)

        spec = apispec.APISpec(
            title="HyperLeda API specification",
            version="1.0.0",
            openapi_version="3.0.2",
            plugins=[apimarshmallow.MarshmallowPlugin(), apiaiohttp.AiohttpPlugin()],
        )
        spec.components.security_scheme("TokenAuth", {"type": "http", "scheme": "bearer"})

        for route_description in routes:
            log.debug(
                "init handler",
                method=route_description.method(),
                path=route_description.path(),
            )
            route = app.router.add_route(
                route_description.method(),
                route_description.path(),
                route_description.handler(),
            )

            request_schema = route_description.request_schema()
            response_schema = route_description.response_schema()

            if request_schema.__name__ not in spec.components.schemas:
                spec.components.schema(request_schema.__name__, schema=request_schema)

            if response_schema.__name__ not in spec.components.schemas:
                spec.components.schema(response_schema.__name__, schema=response_schema)

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

        self.app = app

    def run(self, cfg: config.ServerConfig):
        log.info(
            "starting server",
            url=f"{cfg.host}:{cfg.port}",
            swagger_ui=f"{cfg.host}:{cfg.port}{config.SWAGGER_UI_URL}",
        )

        web.run_app(self.app, host=cfg.host, port=cfg.port, access_log_class=server.AccessLogger)
