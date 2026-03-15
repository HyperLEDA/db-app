import unittest

from parameterized import parameterized

import app.commands.adminapi.command as adminapi
import app.commands.dataapi.command as dataapi


class TestEnvironment(unittest.TestCase):
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
