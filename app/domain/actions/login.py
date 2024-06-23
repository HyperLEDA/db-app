import app.domain.model as domain_model
from app import commands
from app.lib.exceptions import new_unauthorized_error


def login(depot: commands.Depot, r: domain_model.LoginRequest) -> domain_model.LoginResponse:
    token, is_authenticated = depot.authenticator.login(r.username, r.password)

    if not is_authenticated:
        raise new_unauthorized_error("invalid username or password")

    return domain_model.LoginResponse(token=token)
