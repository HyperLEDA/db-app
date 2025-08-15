import sys
import unittest
from pathlib import Path

from parameterized import parameterized

import app.commands.adminapi.command as adminapi
import app.commands.dataapi.command as dataapi
import app.commands.runtask.command as runtask

REQUIREMENTS_PATH = Path("requirements.txt")
MINIMAL_PYTHON_VERSION = (3, 10)


class TestEnvironment(unittest.TestCase):
    def test_python_version(self):
        self.assertGreaterEqual(
            sys.version_info,
            MINIMAL_PYTHON_VERSION,
            msg=f"You are using Python with version {'.'.join(map(str, sys.version_info))}"
            f"while minimally supported version is {'.'.join(map(str, MINIMAL_PYTHON_VERSION))}",
        )

    @parameterized.expand(
        [
            ("configs/dev/adminapi.yaml"),
            ("configs/test/adminapi.yaml"),
            ("configs/prod/adminapi.yaml"),
        ]
    )
    def test_parse_adminapi_config(self, path):
        _ = adminapi.parse_config(path)

    @parameterized.expand(
        [
            ("configs/dev/dataapi.yaml"),
            ("configs/test/dataapi.yaml"),
            ("configs/prod/dataapi.yaml"),
        ]
    )
    def test_parse_dataapi_config(self, path):
        _ = dataapi.parse_config(path)

    @parameterized.expand(
        [
            ("configs/dev/tasks.yaml"),
        ]
    )
    def test_parse_runtask_config(self, path):
        _ = runtask.parse_config(path)
