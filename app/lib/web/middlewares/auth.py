from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass

import fastapi
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.web import errors

AUTH_CTX_STATE_ATTR = "auth_ctx"
REMOTE_USER_HEADER = "Remote-User"


@dataclass(frozen=True)
class AuthContext:
    login: str


def identity_from_request(request: fastapi.Request) -> AuthContext | None:
    ctx = getattr(request.state, AUTH_CTX_STATE_ATTR, None)
    if isinstance(ctx, AuthContext):
        return ctx
    return None


class AuthMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        secured_routes: Collection[tuple[str, str]],
    ) -> None:
        self._secured_routes = frozenset(secured_routes)
        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        login = request.headers.get(REMOTE_USER_HEADER, "").strip()
        if login:
            setattr(request.state, AUTH_CTX_STATE_ATTR, AuthContext(login=login))

        if (request.url.path, request.method.lower()) in self._secured_routes:
            if identity_from_request(request) is None:
                return _api_error_response(errors.UnauthorizedError("No authenticated user"))

        return await call_next(request)


def _api_error_response(exc: errors.APIError) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(exc.dict(), status_code=exc.status())
