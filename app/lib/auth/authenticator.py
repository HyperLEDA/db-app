import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from app.lib.auth import interface, user
from app.lib.storage import postgres


class NoopAuthenticator(interface.Authenticator):
    """
    This is a testing authenticator that successfully authenticates all users as admins.
    """

    def login(self, username: str, password: str) -> tuple[str, bool]:
        return "noop_token", True

    def authenticate(self, token: str) -> tuple[user.User, bool]:
        return user.User(1, user.Role.ADMIN), True


class PostgresAuthenticator(interface.Authenticator):
    """
    Authenticates users and stores authentication data in Postgres database.
    Default token lifetime is 14 days.
    """

    def __init__(self, storage: postgres.PgStorage, token_lifetime_seconds: int = 14 * 24 * 60 * 60):
        self._storage = storage
        self._storage.register_type(user.Role, "common.user_role")
        self.token_lifetime = token_lifetime_seconds

    def login(self, username: str, password: str) -> tuple[str, bool]:
        try:
            user_info = self._storage.query_one(
                "SELECT id, password_hash FROM common.users WHERE login = %s",
                params=[username],
            )
        except RuntimeError:
            return "", False

        expected_password_hash = user_info["password_hash"]
        password_matches = bcrypt.checkpw(str.encode(password), expected_password_hash)

        if not password_matches:
            return "", False

        token = secrets.token_hex(16)

        self._storage.exec(
            "INSERT INTO common.tokens (token, user_id, expiry_time) VALUES (%s, %s, %s)",
            params=[
                token,
                user_info["id"],
                datetime.now(timezone.utc) + timedelta(seconds=self.token_lifetime),
            ],
        )
        return token, True

    def authenticate(self, token: str) -> tuple[user.User, bool]:
        try:
            token_info = self._storage.query_one(
                """
                SELECT t.token AS token, u.id AS user_id, u.role AS role
                FROM common.tokens AS t
                JOIN common.users AS u ON t.user_id = u.id
                WHERE t.token = %s AND t.expiry_time > %s AND t.active
                """,
                params=[token, datetime.now(timezone.utc)],
            )
        except RuntimeError:
            return None, False

        return user.User(token_info["user_id"], token_info["role"]), True
