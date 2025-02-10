import abc

from app.lib.auth import user


class Authenticator(abc.ABC):
    """
    This interface is responsible for providing the means to authenticate users.
    """

    @abc.abstractmethod
    def login(self, username: str, password: str) -> tuple[str, bool]:
        """
        Given username and password, returns a token and a boolean indicating if the user is authenticated.
        """

    @abc.abstractmethod
    def authenticate(self, token: str) -> tuple[user.User, bool]:
        """
        Given a token, returns the boolean indicating if the user is authenticated and if they are,
        instance of the user.
        """
