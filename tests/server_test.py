import subprocess
import unittest
from time import sleep

import requests

from app.presentation.commands.runserver import config


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.process = subprocess.Popen(
            [
                "python",
                "main.py",
                "runserver",
                "-c",
                "configs/dev/config.yaml",
            ]
        )
        sleep(0.5)

    def tearDown(self) -> None:
        self.process.kill()
        self.process.wait()
        return super().tearDown()

    def test_parse_configs(self):
        config_paths = [
            "configs/dev/config.yaml",
        ]

        for path in config_paths:
            _ = config.parse_config(path)

    def test_startup(self):
        response = requests.get("http://localhost:8000/ping", timeout=2)
        data = response.json()

        self.assertDictEqual(data, {"ping": "pong"})
