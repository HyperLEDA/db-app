from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import fastapi
from fastapi.security import http as http_security

from app.lib import auth
from app.lib.web import errors

_bearer = http_security.HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: auth.User
    token: str


def make_require_roles(
    authenticator: auth.Authenticator,
    allowed: list[auth.Role],
) -> Callable[..., AuthContext]:
    def require_roles(
        creds: Annotated[
            http_security.HTTPAuthorizationCredentials | None,
            fastapi.Depends(_bearer),
        ],
    ) -> AuthContext:
        if creds is None or creds.scheme.lower() != "bearer":
            raise errors.UnauthorizedError("No authorization header")
        user, ok = authenticator.authenticate(creds.credentials)
        if not ok:
            raise errors.UnauthorizedError("Invalid token")
        if not allowed:
            raise errors.ForbiddenError("Not enough permissions")
        if user.role not in allowed:
            raise errors.ForbiddenError("Not enough permissions")
        return AuthContext(user=user, token=creds.credentials)

    return require_roles
