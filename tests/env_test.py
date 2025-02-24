import sys
import unittest
from pathlib import Path

from parameterized import parameterized

import app.commands.adminapi.config as adminapi_config
import app.commands.dataapi.config as dataapi_config
import app.commands.runtask.config as runtask_config

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
        ]
    )
    def test_parse_adminapi_config(self, path):
        _ = adminapi_config.parse_config(path)

    @parameterized.expand(
        [
            ("configs/dev/dataapi.yaml"),
            ("configs/test/dataapi.yaml"),
        ]
    )
    def test_parse_dataapi_config(self, path):
        _ = dataapi_config.parse_config(path)

    @parameterized.expand(
        [
            ("configs/dev/tasks.yaml"),
        ]
    )
    def test_parse_runtask_config(self, path):
        _ = runtask_config.parse_config(path)
