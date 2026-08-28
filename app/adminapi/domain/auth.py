import bcrypt
from psycopg import sql

from app.lib import auth
from app.lib.storage import postgres
from app.lib.web.errors import ConflictError, UnauthorizedError
from app.specs import adminapi as spec


class AuthManager(postgres.TransactionalPGRepository):
    def __init__(self, authenticator: auth.Authenticator, storage: postgres.PgStorage) -> None:
        super().__init__(storage)
        self.authenticator = authenticator

    def login(self, r: spec.LoginRequest) -> spec.LoginResponse:
        token, is_authenticated = self.authenticator.login(r.username, r.password)

        if not is_authenticated:
            raise UnauthorizedError("invalid username or password")

        return spec.LoginResponse(token=token)

    def logout(self, token: str) -> spec.LogoutResponse:
        self.authenticator.revoke(token)
        return spec.LogoutResponse()

    def register(self, r: spec.RegisterRequest) -> spec.RegisterResponse:
        self._ensure_available(r.username, r.email)

        password_hash = bcrypt.hashpw(r.password.encode(), bcrypt.gensalt())

        with self.with_tx():
            self._storage.exec(
                "INSERT INTO private.users (login, name, email, role, password_hash) VALUES (%s, %s, %s, 'admin', %s)",
                params=[r.username, r.username, r.email, password_hash],
            )
            self._storage.exec(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(r.username),
                    sql.Literal(r.password),
                )
            )
            self._storage.exec(sql.SQL("GRANT db_reader TO {}").format(sql.Identifier(r.username)))

        return spec.RegisterResponse()

    def _ensure_available(self, username: str, email: str) -> None:
        existing = self._storage.query(
            "SELECT login, email FROM private.users WHERE login = %s OR email = %s",
            params=[username, email],
        )
        if existing:
            if existing[0]["login"] == username:
                raise ConflictError(f"user '{username}' already exists")
            raise ConflictError(f"email '{email}' already exists")

        role_exists = self._storage.query(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            params=[username],
        )
        if role_exists:
            raise ConflictError(f"database user '{username}' already exists")
