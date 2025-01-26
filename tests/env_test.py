import sys
import unittest
from pathlib import Path

from parameterized import parameterized

from app.commands.runserver import config

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

    @parameterized.expand([("configs/dev/config.yaml")])
    def test_parse_config(self, path):
        _ = config.parse_config(path)
