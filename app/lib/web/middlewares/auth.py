from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import fastapi
from starlette import types
from starlette.middleware import base as middlewares

from app.lib import auth
from app.lib.web import errors

AUTH_CTX_STATE_ATTR = "auth_ctx"


@dataclass
class AuthContext:
    user: auth.User
    token: str


def identity_from_request(request: fastapi.Request) -> AuthContext | None:
    ctx = getattr(request.state, AUTH_CTX_STATE_ATTR, None)
    if isinstance(ctx, AuthContext):
        return ctx
    return None


def _parse_bearer_token(request: fastapi.Request) -> str | None:
    raw = request.headers.get("Authorization", "").strip()
    parts = raw.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token if token else None


class AuthMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        secured_roles: Mapping[tuple[str, str], frozenset[auth.Role]],
    ) -> None:
        self._secured_roles = secured_roles
        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        token = _parse_bearer_token(request)
        if token is not None:
            authenticator = request.app.state.authenticator
            user, ok = authenticator.authenticate(token)
            if ok:
                setattr(
                    request.state,
                    AUTH_CTX_STATE_ATTR,
                    AuthContext(user=user, token=token),
                )

        allowed = self._secured_roles.get((request.url.path, request.method.lower()))
        if allowed is not None:
            ctx = identity_from_request(request)
            if ctx is None:
                return _api_error_response(errors.UnauthorizedError("No authorization header"))
            if not allowed:
                return _api_error_response(errors.ForbiddenError("Not enough permissions"))
            if ctx.user.role not in allowed:
                return _api_error_response(errors.ForbiddenError("Not enough permissions"))

        return await call_next(request)


def _api_error_response(exc: errors.APIError) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(exc.dict(), status_code=exc.status())
