import os
import subprocess
import sys
import time
import unittest
from concurrent import futures

import requests
import structlog

from tests import lib

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class DataAPIServerTest(unittest.TestCase):
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

        logger.info("starting server", port=cls.server_port)

        cls.process = subprocess.Popen(
            [
                sys.executable,
                "main.py",
                "dataapi",
                "-c",
                "configs/dev/dataapi.yaml",
            ],
            stdout=sys.stderr,
            stderr=sys.stderr,
        )
        # give process some time to set up properly
        time.sleep(2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.kill()
        cls.process.wait()

    def test_startup(self):
        response = requests.get(f"http://localhost:{self.server_port}/ping", timeout=2)
        data = response.json()

        self.assertDictEqual(data, {"data": {"ping": "pong"}})
