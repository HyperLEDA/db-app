import http
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import fastapi
import pydantic
import structlog
import uvicorn

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


class FastAPIServer:
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
        )

        for route in routes:
            app.add_api_route(
                path=f"/api{route.path}",
                endpoint=route.handler,
                methods=[route.method],
                summary=route.summary,
                description=route.description,
            )

        app.add_api_route("/ping", lambda: {"data": {"ping": "pong"}})

        self.app = app
        self.config = cfg
        self.logger = logger

        self.logger.debug("initialized server", n_routes=len(routes))

    def run(self):
        self.logger.info(
            "starting server",
            url=f"{self.config.host}:{self.config.port}",
            swagger_ui=f"{self.config.host}:{self.config.port}{self.config.swagger_ui_path}",
        )

        uvicorn.run(self.app, host=self.config.host, port=self.config.port)
