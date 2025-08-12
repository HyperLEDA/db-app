from collections.abc import Awaitable, Callable

import fastapi
import structlog
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.web import errors


class ExceptionMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self.logger = logger

        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ):
        try:
            return await call_next(request)
        except errors.APIError as e:
            exc = e
        except Exception as e:
            exc = errors.InternalError(str(e))

        self.logger.exception(str(exc))
        return fastapi.responses.JSONResponse(exc.dict())
