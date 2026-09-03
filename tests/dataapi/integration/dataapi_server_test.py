import os
import pathlib
import subprocess
import tempfile
import time
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
class DataAPIServer:
    server_port: int
    process: subprocess.Popen[bytes]
    stdout_file: object
    stderr_file: object


@pytest.fixture(scope="module")
def dataapi_server(pg_storage: PostgresTestStorage) -> Generator[DataAPIServer]:
    with futures.ThreadPoolExecutor() as group:
        port_thread = group.submit(lib.find_free_port)

    server_port = port_thread.result()

    temp_dir = tempfile.mkdtemp()
    stdout_path = pathlib.Path(temp_dir) / "stdout.log"
    stderr_path = pathlib.Path(temp_dir) / "stderr.log"

    stdout_file = stdout_path.open("w")
    stderr_file = stderr_path.open("w")

    os.environ["SERVER_PORT"] = str(server_port)
    os.environ["STORAGE_ENDPOINT"] = "localhost"
    os.environ["STORAGE_PORT"] = str(pg_storage.port)
    os.environ["STORAGE_USER"] = "hyperleda_reader"
    os.environ["STORAGE_PASSWORD"] = "password"

    logger.info("starting server", port=server_port)

    process = subprocess.Popen(
        [
            "uv",
            "run",
            "dataapi",
            "-c",
            "configs/dev/dataapi.yaml",
        ],
        stdout=stdout_file,
        stderr=stderr_file,
    )
    time.sleep(2)

    if process.poll() is not None and process.returncode != 0:
        raise RuntimeError(f"""Process failed to start.
STDOUT: {stdout_path}
STDERR: {stderr_path}""")

    server = DataAPIServer(
        server_port=server_port,
        process=process,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
    )
    yield server

    process.kill()
    process.wait()
    stdout_file.close()
    stderr_file.close()


def test_startup(dataapi_server: DataAPIServer) -> None:
    response = requests.get(f"http://localhost:{dataapi_server.server_port}/ping", timeout=2)
    data = response.json()

    assert data == {"data": {"ping": "pong"}}
