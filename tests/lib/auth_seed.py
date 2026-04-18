import bcrypt

from app.lib.storage import postgres


def seed_admin_user(storage: postgres.PgStorage, login: str, password: str) -> None:
    storage.exec(
        "DELETE FROM common.tokens WHERE user_id IN (SELECT id FROM common.users WHERE login = %s)",
        params=[login],
    )
    storage.exec("DELETE FROM common.users WHERE login = %s", params=[login])
    storage.exec(
        "INSERT INTO common.users (login, name, email, role, password_hash) VALUES (%s, %s, %s, 'admin', %s)",
        params=[
            login,
            login,
            f"{login}@test.local",
            bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        ],
    )
