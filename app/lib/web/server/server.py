import http
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import fastapi
import pydantic
import structlog
import uvicorn
from fastapi import exceptions, responses
from fastapi.middleware import cors
from fastapi.openapi import utils as openapi_utils
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.lib import auth
from app.lib.web import errors, middlewares
from app.lib.web.dependencies import auth as auth_dependencies
from app.lib.web.server import config


class APIOkResponse[T: Any](pydantic.BaseModel):
    data: T


@dataclass
class Route[ReqT: pydantic.BaseModel, RespT: pydantic.BaseModel]:
    path: str
    method: http.HTTPMethod
    handler: Callable[..., APIOkResponse[RespT] | fastapi.Response]
    summary: str
    description: str = ""
    allowed_roles: list[auth.Role] | None = None
    rate_limit: str | None = None


async def validation_exception_handler(_request, exc):
    err = errors.RuleValidationError(str(exc))

    return responses.JSONResponse(err.dict(), status_code=err.status())


async def rate_limit_exception_handler(_request, exc: RateLimitExceeded):
    err = errors.RuleValidationError(str(exc))
    return responses.JSONResponse(err.dict(), status_code=429)


def _secured_path_methods(routes: list[Route[Any, Any]], path_prefix: str) -> frozenset[tuple[str, str]]:
    return frozenset(
        (f"{path_prefix}{route.path}", route.method.value.lower())
        for route in routes
        if route.allowed_roles is not None
    )


def _make_openapi(app: fastapi.FastAPI, secured: frozenset[tuple[str, str]]) -> Callable[[], dict[str, Any]]:
    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = openapi_utils.get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )
        components = openapi_schema.setdefault("components", {})
        schemes = components.setdefault("securitySchemes", {})
        schemes.setdefault("HTTPBearer", {"type": "http", "scheme": "bearer"})
        http_methods = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace"})
        for path, path_item in (openapi_schema.get("paths") or {}).items():
            for method, operation in path_item.items():
                if method not in http_methods:
                    continue
                if (path, method) in secured:
                    operation["security"] = [{"HTTPBearer": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return openapi


class WebServer:
    def __init__(
        self,
        routes: list[Route],
        cfg: config.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
        authenticator: auth.Authenticator,
        enforce_route_auth: bool = True,
    ) -> None:
        app = fastapi.FastAPI(
            docs_url=f"{cfg.path_prefix}/docs",
            openapi_url=f"{cfg.path_prefix}/openapi.json",
            redoc_url=f"{cfg.path_prefix}/redoc",
            title="HyperLEDA API",
            swagger_ui_parameters={
                "tryItOutEnabled": True,
                "displayRequestDuration": True,
                "persistAuthorization": True,
            },
        )
        self.limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = self.limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

        app.add_middleware(middlewares.ExceptionMiddleware, logger=logger)
        app.add_middleware(middlewares.LoggingMiddleware, logger=logger)
        app.add_middleware(
            cors.CORSMiddleware,
            allow_origins=cfg.allowed_origins,
            allow_credentials=False,
            allow_headers=["Content-Type", "Authorization"],
            allow_methods=[
                http.HTTPMethod.GET,
                http.HTTPMethod.POST,
                http.HTTPMethod.PUT,
                http.HTTPMethod.PATCH,
                http.HTTPMethod.DELETE,
                http.HTTPMethod.OPTIONS,
            ],
        )

        for route in routes:
            route_dependencies: list[Any] = []
            endpoint = route.handler
            if route.rate_limit is not None:
                endpoint = self.limiter.limit(route.rate_limit)(endpoint)
            if enforce_route_auth and route.allowed_roles is not None:
                role_dep = auth_dependencies.make_require_roles(authenticator, route.allowed_roles)
                route_dependencies.append(fastapi.Depends(role_dep))
            app.add_api_route(
                path=f"{cfg.path_prefix}{route.path}",
                endpoint=endpoint,
                methods=[route.method],
                summary=route.summary,
                description=route.description,
                operation_id=endpoint.__name__,
                response_model_exclude_none=True,
                response_model_exclude_unset=True,
                dependencies=route_dependencies,
            )

        app.add_api_route(
            path="/ping",
            endpoint=lambda: {"data": {"ping": "pong"}},
            summary="Check that service is up and running",
        )

        app.add_exception_handler(exceptions.RequestValidationError, validation_exception_handler)

        FastAPIInstrumentor.instrument_app(app)

        app.openapi = _make_openapi(app, _secured_path_methods(routes, cfg.path_prefix))

        self.app = app
        self.config = cfg
        self.logger = logger

        self.logger.debug("initialized server", n_routes=len(routes))

    def run(self):
        self.logger.info(
            "starting server",
            url=f"{self.config.host}:{self.config.port}",
            swagger_ui=f"'http://{self.config.host}:{self.config.port}{self.app.docs_url}'",
        )

        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_config=None,
        )
