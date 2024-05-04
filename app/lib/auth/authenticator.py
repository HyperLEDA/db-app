from app.lib.auth import interface, user


class NoopAuthenticator(interface.Authenticator):
    """
    This is a testing authenticator that successfully authenticates all users as admins.
    """

    def login(self, username: str, password: str) -> tuple[str, bool]:
        return "noop_token", True

    def authenticate(self, token: str) -> tuple[user.User, bool]:
        return user.User(1, user.Role.ADMIN), True
