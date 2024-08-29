import unittest
from unittest import mock

import structlog
from parameterized import param, parameterized

from app.data.repositories import Layer0Repository


class Layer0RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_mock = mock.MagicMock()
        self.repo = Layer0Repository(self.storage_mock, structlog.get_logger())

    @parameterized.expand(
        [
            param("no kwargs", {}, "SELECT * FROM rawdata.ironman OFFSET %s"),
            param("with columns", {"columns": ["one", "two"]}, "SELECT one, two FROM rawdata.ironman OFFSET %s"),
            param(
                "with order by",
                {"order_column": "one", "order_direction": "desc"},
                "SELECT * FROM rawdata.ironman ORDER BY one DESC OFFSET %s",
            ),
            param("with limit", {"limit": 10}, "SELECT * FROM rawdata.ironman OFFSET %s LIMIT %s"),
            param(
                "with all",
                {"columns": ["one", "two"], "order_column": "one", "order_direction": "desc", "limit": 10},
                "SELECT one, two FROM rawdata.ironman ORDER BY one DESC OFFSET %s LIMIT %s",
            ),
        ]
    )
    def test_fetch_raw_data(self, name: str, kwargs: dict, expected_query: str):
        self.storage_mock.query_one.return_value = {"table_name": "ironman"}
        self.storage_mock.query.return_value = {"haha": [1, 2]}

        _ = self.repo.fetch_raw_data(10, **kwargs)
        args, _ = self.storage_mock.query.call_args

        def transform(s):
            return " ".join(s.replace("\n", " ").replace(", ", ",").lower().split())

        actual = transform(args[0])
        expected = transform(expected_query)

        self.assertEqual(actual, expected)
