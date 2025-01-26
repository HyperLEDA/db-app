from app import schema
from app.commands.adminapi import depot
from app.lib.web.errors import UnauthorizedError


def login(dpt: depot.Depot, r: schema.LoginRequest) -> schema.LoginResponse:
    token, is_authenticated = dpt.authenticator.login(r.username, r.password)

    if not is_authenticated:
        raise UnauthorizedError("invalid username or password")

    return schema.LoginResponse(token=token)
