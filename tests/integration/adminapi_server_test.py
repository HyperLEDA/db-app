import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent import futures

import requests
import structlog

from tests import lib

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class AdminAPIServerTest(unittest.TestCase):
    """
    Tests server startup.
    """

    @classmethod
    def setUpClass(cls) -> None:
        with futures.ThreadPoolExecutor() as group:
            pg_thread = group.submit(lib.TestPostgresStorage.get)
            port_thread = group.submit(lib.find_free_port)

        cls.pg_storage = pg_thread.result()
        cls.server_port = port_thread.result()

        os.environ["SERVER_PORT"] = str(cls.server_port)
        os.environ["STORAGE_PORT"] = str(cls.pg_storage.port)
        os.environ["CLIENTS_ADS_TOKEN"] = "test"

        logger.info("starting server", port=cls.server_port)

        cls.temp_dir = tempfile.mkdtemp()
        cls.stdout_path = pathlib.Path(cls.temp_dir) / "stdout.log"
        cls.stderr_path = pathlib.Path(cls.temp_dir) / "stderr.log"

        cls.stdout_file = cls.stdout_path.open("w")
        cls.stderr_file = cls.stderr_path.open("w")

        cls.process = subprocess.Popen(
            [
                sys.executable,
                "main.py",
                "adminapi",
                "-c",
                "configs/dev/adminapi.yaml",
            ],
            stdout=cls.stdout_file,
            stderr=cls.stderr_file,
        )
        # give process some time to set up properly
        time.sleep(2)

        if cls.process.poll() is not None and cls.process.returncode != 0:
            raise RuntimeError(f"""Process failed to start.
STDOUT: {cls.stdout_path}
STDERR: {cls.stderr_path}""")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.kill()
        cls.process.wait()

        cls.stdout_file.close()
        cls.stderr_file.close()

    def test_startup(self):
        response = requests.get(f"http://localhost:{self.server_port}/ping", timeout=2)

        data = response.json()
        self.assertDictEqual(data, {"data": {"ping": "pong"}})
