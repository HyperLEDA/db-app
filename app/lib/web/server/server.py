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
from starlette.middleware import base as smiddlewares

from app.lib.web import errors, middlewares
from app.lib.web.server import config


class APIOkResponse[T: Any](pydantic.BaseModel):
    data: T


@dataclass
class Route[ReqT: pydantic.BaseModel, RespT: pydantic.BaseModel]:
    path: str
    method: http.HTTPMethod
    handler: Callable[[ReqT], APIOkResponse[RespT] | fastapi.Response]
    summary: str
    description: str = ""


async def validation_exception_handler(request, exc):
    err = errors.RuleValidationError(str(exc))

    return responses.JSONResponse(err.dict(), status_code=err.status())


class WebServer:
    def __init__(
        self,
        routes: list[Route],
        cfg: config.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        app = fastapi.FastAPI(
            docs_url=f"{cfg.path_prefix}/docs",
            openapi_url=f"{cfg.path_prefix}/openapi.json",
            redoc_url=f"{cfg.path_prefix}/redoc",
            title="HyperLEDA API",
            
        )

        app.add_middleware(middlewares.ExceptionMiddleware, logger=logger)
        app.add_middleware(middlewares.LoggingMiddleware, logger=logger)
        app.add_middleware(
            cors.CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_headers=["Content-Type", "Authorization"],
            allow_methods=[
                http.HTTPMethod.GET,
                http.HTTPMethod.POST,
                http.HTTPMethod.PUT,
                http.HTTPMethod.DELETE,
                http.HTTPMethod.OPTIONS,
            ],
        )

        for route in routes:
            app.add_api_route(
                path=f"{cfg.path_prefix}{route.path}",
                endpoint=route.handler,
                methods=[route.method],
                summary=route.summary,
                description=route.description,
            )

        app.add_api_route(
            path="/ping",
            endpoint=lambda: {"data": {"ping": "pong"}},
            summary="Check that service is up and running",
        )

        app.add_exception_handler(exceptions.RequestValidationError, validation_exception_handler)

        self.app = app
        self.config = cfg
        self.logger = logger

        self.logger.debug("initialized server", n_routes=len(routes))

    def add_mw(self, mw: type[smiddlewares.BaseHTTPMiddleware], *args, **kwargs):
        self.app.add_middleware(mw, *args, **kwargs)

    def run(self):
        self.logger.info(
            "starting server",
            url=f"{self.config.host}:{self.config.port}",
            swagger_ui={self.app.docs_url}
        )

        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_config=None,
        )
