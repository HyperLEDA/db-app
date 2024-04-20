import sys
import unittest
from pathlib import Path

import pkg_resources
from parameterized import parameterized

from app.presentation.commands.runserver import config

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

    def test_requirements(self):
        with REQUIREMENTS_PATH.open(encoding="utf-8") as reqs_file:
            requirements = pkg_resources.parse_requirements(reqs_file)

            try:
                pkg_resources.require(map(str, requirements))
            except pkg_resources.DistributionNotFound as e:
                raise AssertionError(
                    f"The 'requirements.txt' file lists the '{e.args[0]}' package, but it is not installed "
                    "in your Python environment. It is possible that the list of required modules has been "
                    "updated since the last time you ran the test suite. To ensure that all necessary "
                    "packages are installed, please run `make install`.",
                ) from e

    @parameterized.expand([("configs/dev/config.yaml")])
    def test_parse_config(self, path):
        _ = config.parse_config(path)
