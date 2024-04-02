import unittest
from pathlib import Path

import pkg_resources
from parameterized import parameterized

from app.presentation.commands.runserver import config

REQUIREMENTS_PATH = Path("requirements.txt")


class TestEnvironment(unittest.TestCase):
    def test_requirements(self):
        with REQUIREMENTS_PATH.open() as reqs_file:
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
