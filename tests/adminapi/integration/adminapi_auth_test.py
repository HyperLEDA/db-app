import hashlib
import os
import secrets
import subprocess
import time
from collections.abc import Generator
from concurrent import futures
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
import requests
import structlog
from psycopg import sql

from app.lib import audit
from tests import lib
from tests.lib import auth_seed
from tests.lib.postgres import TestPostgresStorage

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_LOGIN = "integration_auth_admin"
_PASSWORD = "integration-secret"
_REGISTERED_LOGIN = "integration_registered_user"
_REGISTERED_EMAIL = "integration_registered_user@example.com"
_REGISTERED_PASSWORD = "registered-user-secret"


@dataclass
class AdminAPIAuthServer:
    server_port: int
    process: subprocess.Popen[bytes]
    pg_storage: TestPostgresStorage


@pytest.fixture(scope="module")
def adminapi_auth_server(pg_storage: TestPostgresStorage) -> Generator[AdminAPIAuthServer]:
    with futures.ThreadPoolExecutor() as group:
        port_thread = group.submit(lib.find_free_port)

    server_port = port_thread.result()

    auth_seed.seed_admin_user(pg_storage.get_storage(), _LOGIN, _PASSWORD)

    os.environ["SERVER_PORT"] = str(server_port)
    os.environ["STORAGE_ENDPOINT"] = "localhost"
    os.environ["STORAGE_PORT"] = str(pg_storage.port)
    os.environ["CLIENTS_ADS_TOKEN"] = "test"
    os.environ["AUTH_ENABLED"] = "true"

    logger.info("starting adminapi for auth tests", port=server_port)

    process = subprocess.Popen(
        [
            "uv",
            "run",
            "adminapi",
            "-c",
            "configs/dev/adminapi.yaml",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{server_port}/ping", timeout=1)
            if r.status_code == 200:
                break
        except (requests.RequestException, OSError):
            pass
        time.sleep(0.3)
        if process.poll() is not None and process.returncode != 0:
            raise RuntimeError("adminapi process exited before becoming ready")
    else:
        process.kill()
        raise RuntimeError("adminapi did not respond on /ping within 30s")

    server = AdminAPIAuthServer(server_port=server_port, process=process, pg_storage=pg_storage)
    yield server

    process.kill()
    process.wait()

    storage = pg_storage.get_storage()
    storage.exec(
        "DELETE FROM private.tokens WHERE user_id IN (SELECT id FROM private.users WHERE login = %s)",
        params=[_LOGIN],
    )
    storage.exec("DELETE FROM private.users WHERE login = %s", params=[_LOGIN])


def _base(server: AdminAPIAuthServer) -> str:
    return f"http://127.0.0.1:{server.server_port}/admin/api"


def test_get_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.get(f"{_base(adminapi_auth_server)}/v1/tables", timeout=5)
    assert r.status_code == 401
    assert r.json()["message"] == "No authorization header"


def test_post_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.post(
        f"{_base(adminapi_auth_server)}/v1/source",
        json={"title": "t", "authors": ["A"], "year": 2020},
        timeout=5,
    )
    assert r.status_code == 401
    assert r.json()["message"] == "No authorization header"


def test_patch_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.patch(
        f"{_base(adminapi_auth_server)}/v1/table",
        json={"table_name": "nope", "columns": {}},
        timeout=5,
    )
    assert r.status_code == 401


def test_login_wrong_password(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.post(
        f"{_base(adminapi_auth_server)}/v1/login",
        json={"username": _LOGIN, "password": "wrong"},
        timeout=5,
    )
    assert r.status_code == 401


def _login_and_get_token(server: AdminAPIAuthServer) -> str:
    r = requests.post(
        f"{_base(server)}/v1/login",
        json={"username": _LOGIN, "password": _PASSWORD},
        timeout=5,
    )
    assert r.status_code == 200
    return r.json()["data"]["token"]


def _seed_bearer_token(server: AdminAPIAuthServer, login: str) -> str:
    storage = server.pg_storage.get_storage()
    user = storage.query_one(
        "SELECT id FROM private.users WHERE login = %s",
        params=[login],
    )
    token = secrets.token_hex(16)
    storage.exec(
        "INSERT INTO private.tokens (token_hash, user_id, expiry_time) VALUES (%s, %s, %s)",
        params=[
            hashlib.sha256(token.encode()).digest(),
            user["id"],
            datetime.now(UTC) + timedelta(days=14),
        ],
    )
    return token


def _assert_token_works(server: AdminAPIAuthServer, token: str) -> None:
    r = requests.post(
        f"{_base(server)}/v1/source",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "t", "authors": ["A"], "year": 2020},
        timeout=5,
    )
    assert r.status_code == 200


def _assert_token_rejected(server: AdminAPIAuthServer, token: str) -> None:
    r = requests.post(
        f"{_base(server)}/v1/source",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "t", "authors": ["A"], "year": 2020},
        timeout=5,
    )
    assert r.status_code == 401
    assert r.json()["message"] == "Invalid token"


def _user_id(server: AdminAPIAuthServer) -> int:
    row = server.pg_storage.get_storage().query_one(
        "SELECT id FROM private.users WHERE login = %s",
        params=[_LOGIN],
    )
    return int(row["id"])


def _post_source(
    server: AdminAPIAuthServer,
    token: str,
    *,
    title: str,
    action_description: str | None = None,
) -> None:
    body: dict[str, object] = {"title": title, "authors": ["A"], "year": 2020}
    if action_description is not None:
        body["action_description"] = action_description
    r = requests.post(
        f"{_base(server)}/v1/source",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=5,
    )
    assert r.status_code == 200


def test_action_log(adminapi_auth_server: AdminAPIAuthServer) -> None:
    token = _login_and_get_token(adminapi_auth_server)
    user_id = _user_id(adminapi_auth_server)
    storage = adminapi_auth_server.pg_storage.get_storage()

    action_description = "integration-action-log-run"
    expected_run_id = audit.run_id(user_id, "create_source", action_description)
    _post_source(adminapi_auth_server, token, title="audit-run-1", action_description=action_description)

    logs = storage.query(
        "SELECT method, run_id, request FROM private.action_log WHERE user_id = %s AND run_id = %s",
        params=[user_id, expected_run_id],
    )
    assert len(logs) == 1
    assert logs[0]["method"] == "create_source"
    assert logs[0]["request"] == {
        "title": "audit-run-1",
        "authors": ["A"],
        "year": 2020,
        "action_description": action_description,
    }

    runs = storage.query(
        "SELECT id, action_description FROM private.runs WHERE id = %s",
        params=[expected_run_id],
    )
    assert len(runs) == 1
    assert runs[0]["action_description"] == action_description

    dedup_description = "integration-action-log-dedup"
    dedup_run_id = audit.run_id(user_id, "create_source", dedup_description)
    _post_source(adminapi_auth_server, token, title="audit-dedup-1", action_description=dedup_description)
    _post_source(adminapi_auth_server, token, title="audit-dedup-2", action_description=dedup_description)

    dedup_logs = storage.query(
        "SELECT id FROM private.action_log WHERE user_id = %s AND run_id = %s",
        params=[user_id, dedup_run_id],
    )
    assert len(dedup_logs) == 2
    dedup_runs = storage.query(
        "SELECT id FROM private.runs WHERE id = %s",
        params=[dedup_run_id],
    )
    assert len(dedup_runs) == 1

    before = storage.query(
        "SELECT COUNT(*)::int AS n FROM private.action_log WHERE user_id = %s AND run_id IS NULL",
        params=[user_id],
    )[0]["n"]
    _post_source(adminapi_auth_server, token, title="audit-no-run")
    after = storage.query(
        "SELECT COUNT(*)::int AS n FROM private.action_log WHERE user_id = %s AND run_id IS NULL",
        params=[user_id],
    )[0]["n"]
    assert after == before + 1

    latest = storage.query(
        """
        SELECT method, run_id, request FROM private.action_log
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        params=[user_id],
    )
    assert latest[0]["method"] == "create_source"
    assert latest[0]["run_id"] is None
    assert latest[0]["request"] == {
        "title": "audit-no-run",
        "authors": ["A"],
        "year": 2020,
    }


def test_up_to_three_tokens_are_valid(adminapi_auth_server: AdminAPIAuthServer) -> None:
    token1 = _login_and_get_token(adminapi_auth_server)
    token2 = _login_and_get_token(adminapi_auth_server)
    token3 = _login_and_get_token(adminapi_auth_server)

    _assert_token_works(adminapi_auth_server, token1)
    _assert_token_works(adminapi_auth_server, token2)
    _assert_token_works(adminapi_auth_server, token3)


def test_fourth_token_invalidates_earliest(adminapi_auth_server: AdminAPIAuthServer) -> None:
    token1 = _login_and_get_token(adminapi_auth_server)
    token2 = _login_and_get_token(adminapi_auth_server)
    token3 = _login_and_get_token(adminapi_auth_server)
    token4 = _login_and_get_token(adminapi_auth_server)

    _assert_token_rejected(adminapi_auth_server, token1)
    _assert_token_works(adminapi_auth_server, token2)
    _assert_token_works(adminapi_auth_server, token3)
    _assert_token_works(adminapi_auth_server, token4)


def test_logout_revokes_token(adminapi_auth_server: AdminAPIAuthServer) -> None:
    token = _login_and_get_token(adminapi_auth_server)

    r_out = requests.post(
        f"{_base(adminapi_auth_server)}/v1/logout",
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=5,
    )
    assert r_out.status_code == 200

    _assert_token_rejected(adminapi_auth_server, token)


def _cleanup_registered_user(server: AdminAPIAuthServer) -> None:
    storage = server.pg_storage.get_storage()
    storage.exec(
        "DELETE FROM private.tokens WHERE user_id IN (SELECT id FROM private.users WHERE login = %s)",
        params=[_REGISTERED_LOGIN],
    )
    storage.exec("DELETE FROM private.users WHERE login = %s", params=[_REGISTERED_LOGIN])
    if storage.query("SELECT 1 FROM pg_roles WHERE rolname = %s", params=[_REGISTERED_LOGIN]):
        storage.exec(sql.SQL("DROP ROLE {}").format(sql.Identifier(_REGISTERED_LOGIN)))


def test_register(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.post(
        f"{_base(adminapi_auth_server)}/v1/register",
        json={
            "username": _REGISTERED_LOGIN,
            "email": _REGISTERED_EMAIL,
            "password": _REGISTERED_PASSWORD,
        },
        timeout=5,
    )
    assert r.status_code == 401
    assert r.json()["message"] == "No authorization header"

    _cleanup_registered_user(adminapi_auth_server)
    try:
        admin_token = _seed_bearer_token(adminapi_auth_server, _LOGIN)
        body = {
            "username": _REGISTERED_LOGIN,
            "email": _REGISTERED_EMAIL,
            "password": _REGISTERED_PASSWORD,
        }

        created = requests.post(
            f"{_base(adminapi_auth_server)}/v1/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=body,
            timeout=5,
        )
        assert created.status_code == 200
        assert created.json()["data"] == {}

        storage = adminapi_auth_server.pg_storage.get_storage()
        user = storage.query_one(
            "SELECT login, email, password_hash FROM private.users WHERE login = %s",
            params=[_REGISTERED_LOGIN],
        )
        assert user["login"] == _REGISTERED_LOGIN
        assert user["email"] == _REGISTERED_EMAIL
        assert bcrypt.checkpw(_REGISTERED_PASSWORD.encode(), user["password_hash"])

        role = storage.query_one(
            """
            SELECT r.rolname
            FROM pg_roles AS r
            JOIN pg_auth_members AS am ON r.oid = am.member
            JOIN pg_roles AS m ON am.roleid = m.oid
            WHERE r.rolname = %s AND m.rolname = 'db_reader'
            """,
            params=[_REGISTERED_LOGIN],
        )
        assert role["rolname"] == _REGISTERED_LOGIN

        tokens_before = storage.query(
            "SELECT token_hash FROM private.tokens WHERE user_id = (SELECT id FROM private.users WHERE login = %s)",
            params=[_REGISTERED_LOGIN],
        )
        assert tokens_before == []

        duplicate_username = requests.post(
            f"{_base(adminapi_auth_server)}/v1/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=body,
            timeout=5,
        )
        assert duplicate_username.status_code == 409
        assert "already exists" in duplicate_username.json()["message"]

        duplicate_email = requests.post(
            f"{_base(adminapi_auth_server)}/v1/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "another_registered_user",
                "email": _REGISTERED_EMAIL,
                "password": _REGISTERED_PASSWORD,
            },
            timeout=5,
        )
        assert duplicate_email.status_code == 409
        assert "already exists" in duplicate_email.json()["message"]
    finally:
        _cleanup_registered_user(adminapi_auth_server)
