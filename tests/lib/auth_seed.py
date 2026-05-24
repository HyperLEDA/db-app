import bcrypt

from app.lib.storage import postgres


def seed_admin_user(storage: postgres.PgStorage, login: str, password: str) -> None:
    storage.exec(
        "DELETE FROM private.tokens WHERE user_id IN (SELECT id FROM private.users WHERE login = %s)",
        params=[login],
    )
    storage.exec("DELETE FROM private.users WHERE login = %s", params=[login])
    storage.exec(
        "INSERT INTO private.users (login, name, email, role, password_hash) VALUES (%s, %s, %s, 'admin', %s)",
        params=[
            login,
            login,
            f"{login}@test.local",
            bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        ],
    )
