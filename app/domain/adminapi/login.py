from app.lib import auth
from app.lib.web.errors import UnauthorizedError
from app.presentation import adminapi


class LoginManager:
    def __init__(self, authenticator: auth.Authenticator) -> None:
        self.authenticator = authenticator

    def login(self, r: adminapi.LoginRequest) -> adminapi.LoginResponse:
        token, is_authenticated = self.authenticator.login(r.username, r.password)

        if not is_authenticated:
            raise UnauthorizedError("invalid username or password")

        return adminapi.LoginResponse(token=token)
