import os
import pathlib
import subprocess
import tempfile
from collections.abc import Generator
from concurrent import futures
from dataclasses import dataclass

import pytest
import requests
import structlog

from tests import lib
from tests.lib.postgres import PostgresTestStorage

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


@dataclass
class AdminAPIServer:
    server_port: int
    process: subprocess.Popen[bytes]
    stdout_file: object
    stderr_file: object


@pytest.fixture(scope="module")
def adminapi_server(pg_storage: PostgresTestStorage) -> Generator[AdminAPIServer]:
    with futures.ThreadPoolExecutor() as group:
        port_thread = group.submit(lib.find_free_port)

    server_port = port_thread.result()

    os.environ["SERVER_PORT"] = str(server_port)
    os.environ["STORAGE_ENDPOINT"] = "localhost"
    os.environ["STORAGE_PORT"] = str(pg_storage.port)
    os.environ["STORAGE_USER"] = "hyperleda"
    os.environ["STORAGE_PASSWORD"] = "password"
    os.environ["CLIENTS_ADS_TOKEN"] = "test"
    os.environ["AUTH_ENABLED"] = "false"

    logger.info("starting server", port=server_port)

    temp_dir = tempfile.mkdtemp()
    stdout_path = pathlib.Path(temp_dir) / "stdout.log"
    stderr_path = pathlib.Path(temp_dir) / "stderr.log"

    stdout_file = stdout_path.open("w")
    stderr_file = stderr_path.open("w")

    process = subprocess.Popen(
        [
            "uv",
            "run",
            "adminapi",
            "-c",
            "configs/dev/adminapi.yaml",
        ],
        stdout=stdout_file,
        stderr=stderr_file,
    )
    try:
        try:
            lib.wait_for_server(f"http://127.0.0.1:{server_port}/ping", process=process)
        except RuntimeError as e:
            raise RuntimeError(f"""{e}
STDOUT: {stdout_path}
STDERR: {stderr_path}""") from e
        yield AdminAPIServer(
            server_port=server_port,
            process=process,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
        )
    finally:
        process.kill()
        process.wait()
        stdout_file.close()
        stderr_file.close()


def test_startup(adminapi_server: AdminAPIServer) -> None:
    response = requests.get(f"http://localhost:{adminapi_server.server_port}/ping", timeout=2)

    data = response.json()
    assert data == {"data": {"ping": "pong"}}
