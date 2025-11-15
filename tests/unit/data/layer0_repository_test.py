import unittest
import uuid
from unittest import mock

import structlog
from parameterized import param, parameterized

from app.data.repositories import Layer0Repository
from tests import lib


class Layer0RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_mock = mock.MagicMock()
        self.repo = Layer0Repository(self.storage_mock, structlog.get_logger())

    @parameterized.expand(
        [
            param("no kwargs", {}, 'SELECT * FROM rawdata."ironman"'),
            param("with columns", {"columns": ["one", "two"]}, 'SELECT one, two FROM rawdata."ironman"'),
            param(
                "with order by",
                {"order_column": "one", "order_direction": "desc"},
                'SELECT * FROM rawdata."ironman" ORDER BY one DESC',
            ),
            param("with limit", {"limit": 10}, 'SELECT * FROM rawdata."ironman" LIMIT %s'),
            param(
                "with offset",
                {"offset": uuid.uuid4()},
                'SELECT * FROM rawdata."ironman" WHERE hyperleda_internal_id > %s',
            ),
            param(
                "with all",
                {
                    "columns": ["one", "two"],
                    "order_column": "one",
                    "order_direction": "desc",
                    "offset": uuid.uuid4(),
                    "limit": 10,
                },
                'SELECT one, two FROM rawdata."ironman" WHERE hyperleda_internal_id > %s ORDER BY one DESC LIMIT %s',
            ),
        ]
    )
    def test_fetch_raw_data(self, name: str, kwargs: dict, expected_query: str):
        lib.returns(self.storage_mock.query, {"haha": [1, 2]})

        _ = self.repo.fetch_raw_data("ironman", **kwargs)
        args, _ = self.storage_mock.query.call_args

        def transform(s):
            return " ".join(s.replace("\n", " ").replace(", ", ",").lower().split())

        actual = transform(args[0])
        expected = transform(expected_query)

        self.assertEqual(actual, expected)
