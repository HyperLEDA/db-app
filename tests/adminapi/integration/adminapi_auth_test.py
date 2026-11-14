import os
import subprocess
from collections.abc import Generator
from concurrent import futures
from dataclasses import dataclass

import pytest
import requests
import structlog

from app.lib import audit
from tests import lib
from tests.lib.postgres import PostgresTestStorage

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_LOGIN = "integration_auth_admin"


@dataclass
class AdminAPIAuthServer:
    server_port: int
    process: subprocess.Popen[bytes]
    pg_storage: PostgresTestStorage


@pytest.fixture(scope="module")
def adminapi_auth_server(pg_storage: PostgresTestStorage) -> Generator[AdminAPIAuthServer]:
    with futures.ThreadPoolExecutor() as group:
        port_thread = group.submit(lib.find_free_port)

    server_port = port_thread.result()

    os.environ["SERVER_PORT"] = str(server_port)
    os.environ["STORAGE_ENDPOINT"] = "localhost"
    os.environ["STORAGE_PORT"] = str(pg_storage.port)
    os.environ["STORAGE_USER"] = "hyperleda"
    os.environ["STORAGE_PASSWORD"] = "password"
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
    try:
        lib.wait_for_server(f"http://127.0.0.1:{server_port}/ping", process=process)
        yield AdminAPIAuthServer(server_port=server_port, process=process, pg_storage=pg_storage)
    finally:
        process.kill()
        process.wait()


def _base(server: AdminAPIAuthServer) -> str:
    return f"http://127.0.0.1:{server.server_port}/admin/api"


def _auth_headers(login: str = _LOGIN) -> dict[str, str]:
    return {"Remote-User": login}


def test_get_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.get(f"{_base(adminapi_auth_server)}/v1/tables", timeout=5)
    assert r.status_code == 401
    assert r.json()["message"] == "No authenticated user"


def test_post_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.post(
        f"{_base(adminapi_auth_server)}/v1/source",
        json={"title": "t", "authors": ["A"], "year": 2020},
        timeout=5,
    )
    assert r.status_code == 401
    assert r.json()["message"] == "No authenticated user"


def test_get_with_remote_user(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.get(
        f"{_base(adminapi_auth_server)}/v1/tables",
        headers=_auth_headers(),
        timeout=5,
    )
    assert r.status_code == 200


def test_public_catalogs_without_auth(adminapi_auth_server: AdminAPIAuthServer) -> None:
    r = requests.get(f"{_base(adminapi_auth_server)}/v1/catalogs", timeout=5)
    assert r.status_code == 200


def test_action_log(adminapi_auth_server: AdminAPIAuthServer) -> None:
    storage = adminapi_auth_server.pg_storage.get_storage()
    storage.exec("DELETE FROM private.action_log WHERE username = %s", params=[_LOGIN])
    storage.exec("DELETE FROM private.runs WHERE username = %s", params=[_LOGIN])

    action_description = "auth-test-create-source"
    r = requests.post(
        f"{_base(adminapi_auth_server)}/v1/source",
        headers=_auth_headers(),
        json={
            "title": "Auth test source",
            "authors": ["Tester"],
            "year": 2024,
            "action_description": action_description,
        },
        timeout=5,
    )
    assert r.status_code == 200

    expected_run_id = audit.run_id(_LOGIN, "create_source", action_description)
    rows = storage.query(
        "SELECT method, run_id, request FROM private.action_log WHERE username = %s AND run_id = %s",
        params=[_LOGIN, expected_run_id],
    )
    assert len(rows) == 1
    assert rows[0]["method"] == "create_source"
    assert rows[0]["run_id"] == expected_run_id
