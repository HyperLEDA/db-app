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


def get_router(routes: list[server.Route]) -> tuple[apispec.APISpec, web.UrlDispatcher]:
    spec = apispec.APISpec(
        title="HyperLeda API specification",
        version="1.0.0",
        openapi_version="3.0.2",
        plugins=[apimarshmallow.MarshmallowPlugin(), apiaiohttp.AiohttpPlugin()],
    )
    spec.components.security_scheme("TokenAuth", {"type": "http", "scheme": "bearer"})

    router = web.UrlDispatcher()

    for descr in routes:
        http_routes = web.route(descr.method(), descr.path(), descr.handler()).register(router)

        if len(http_routes) != 1:
            raise RuntimeError(
                f"route {descr.method()} {descr.path()} has {len(http_routes)} subroutes for some reason"
            )

        route = http_routes[0]

        request_schema = descr.request_schema()
        response_schema = descr.response_schema()

        if request_schema.__name__ not in spec.components.schemas:
            spec.components.schema(request_schema.__name__, schema=request_schema)

        if response_schema.__name__ not in spec.components.schemas:
            spec.components.schema(response_schema.__name__, schema=response_schema)

        spec.path(route=route)

    return spec, router


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

        spec, router = get_router(routes)
        app = web.Application(middlewares=middlewares, router=router)

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
