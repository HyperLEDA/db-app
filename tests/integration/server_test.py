import os
import subprocess
import sys
import time
import unittest

import requests
import structlog

import client
from app.lib import testing

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class ServerTest(unittest.TestCase):
    """
    Tests both server startup and client for the server.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()
        cls.redis_queue = testing.get_test_redis_storage()
        cls.server_port = testing.find_free_port()

        os.environ["SERVER_PORT"] = str(cls.server_port)
        os.environ["STORAGE_PORT"] = str(cls.pg_storage.port)
        os.environ["QUEUE_PORT"] = str(cls.redis_queue.port)

        logger.info("starting server", port=cls.server_port)

        # pylint: disable=consider-using-with
        cls.process = subprocess.Popen(
            [
                sys.executable,
                "main.py",
                "runserver",
                "-c",
                "configs/dev/config.yaml",
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

    def test_bibliography_creation(self):
        bibcode = "2024LPICo3040.1692M"
        title = "Dune Sand Mixing in the Huygens and Dragonfly Landing Sites Region, Titan"
        authors = ["Malaska, M. J."]
        year = 2024

        c = client.HyperLedaClient(endpoint=f"http://localhost:{self.server_port}")
        bib_id = c.create_bibliography(
            bibcode=bibcode,
            title=title,
            authors=authors,
            year=year,
        )
        bib = c.get_bibliography(bib_id)
        self.assertEqual(bib.bibcode, bibcode)
        self.assertEqual(bib.title, title)
        self.assertListEqual(bib.authors, authors)
        self.assertEqual(bib.year, year)
