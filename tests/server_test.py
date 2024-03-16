import socket
import subprocess
import unittest
from contextlib import closing
from time import sleep

import requests

from app.presentation.commands.runserver import config


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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
        port = find_free_port()
        response = requests.get(f"http://localhost:{port}/ping", timeout=2)
        data = response.json()

        self.assertDictEqual(data, {"ping": "pong"})
