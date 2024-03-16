import unittest

from app.presentation.commands.runserver import config


class ServerTest(unittest.TestCase):
    def test_parse_configs(self):
        # TODO: parametrize instead of looping
        for path in ["configs/dev/config.yaml"]:
            _ = config.parse_config(path)
