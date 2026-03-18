import datetime
import unittest
import uuid
from unittest import mock

import structlog
from parameterized import param, parameterized
from psycopg import sql

from app.data.repositories import Layer0Repository
from tests import lib


def normalize_query(s: str | sql.Composable) -> str:
    if not isinstance(s, str):
        s = s.as_string(None)
    return " ".join(s.replace("\n", " ").replace(", ", ",").lower().split())


class Layer0RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_mock = mock.MagicMock()
        self.repo = Layer0Repository(self.storage_mock, structlog.get_logger())

    @parameterized.expand(
        [
            param("no kwargs", {}, 'SELECT * FROM "rawdata"."ironman"'),
            param("with columns", {"columns": ["one", "two"]}, 'SELECT "one","two" FROM "rawdata"."ironman"'),
            param(
                "with order by",
                {"order_column": "one", "order_direction": "desc"},
                'SELECT * FROM "rawdata"."ironman" ORDER BY "one" DESC',
            ),
            param("with limit", {"limit": 10}, 'SELECT * FROM "rawdata"."ironman" LIMIT %s'),
            param(
                "with offset",
                {"offset": uuid.uuid4()},
                'SELECT * FROM "rawdata"."ironman" WHERE "hyperleda_internal_id" > %s',
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
                'SELECT "one","two" FROM "rawdata"."ironman" WHERE "hyperleda_internal_id" > %s'
                ' ORDER BY "one" DESC LIMIT %s',
            ),
        ]
    )
    def test_fetch_raw_data(self, _: str, kwargs: dict, expected_query: str):
        lib.returns(self.storage_mock.query, {"haha": [1, 2]})

        _ = self.repo.fetch_raw_data("ironman", **kwargs)
        args, _ = self.storage_mock.query.call_args

        actual = normalize_query(args[0])
        expected = normalize_query(expected_query)

        self.assertEqual(actual, expected)

    def test_search_tables_calls_query_with_expected_structure(self):
        self.storage_mock.query.return_value = [
            {
                "table_name": "my_table",
                "description": "A test table",
                "num_entries": 100,
                "num_fields": 6,
                "modification_dt": datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
            }
        ]

        result = self.repo.search_tables("my_table", page_size=25, page=1)

        self.storage_mock.query.assert_called_once()
        query = self.storage_mock.query.call_args[0][0]
        params = self.storage_mock.query.call_args[1]["params"]

        self.assertIn("layer0.tables", query)
        self.assertIn("meta.table_info", query)
        self.assertIn("ILIKE", query)
        self.assertIn("LIMIT", query)
        self.assertIn("OFFSET", query)
        self.assertEqual(params[-2], 25)
        self.assertEqual(params[-1], 25)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].table_name, "my_table")
        self.assertEqual(result[0].description, "A test table")
        self.assertEqual(result[0].num_entries, 100)
        self.assertEqual(result[0].num_fields, 6)
