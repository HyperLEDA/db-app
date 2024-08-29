from app import commands, schema
from app.lib.web.errors import UnauthorizedError


def login(depot: commands.Depot, r: schema.LoginRequest) -> schema.LoginResponse:
    token, is_authenticated = depot.authenticator.login(r.username, r.password)

    if not is_authenticated:
        raise UnauthorizedError("invalid username or password")

    return schema.LoginResponse(token=token)
