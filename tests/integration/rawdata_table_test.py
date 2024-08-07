import unittest
from unittest import mock

import pandas
import psycopg
import structlog
from pandas import DataFrame

from app import commands
from app.data import repositories
from app.data.model.layer0 import ColumnDescription, Layer0Creation, Layer0RawData
from app.domain import actions, model
from app.lib import auth, testing
from app.lib import clients as libclients
from app.lib.storage import enums
from app.lib.storage.mapping import TYPE_INTEGER, TYPE_TEXT


class RawDataTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls.clients = libclients.Clients("")
        cls.clients.ads = mock.MagicMock()

        cls.depot = commands.Depot(
            common_repo,
            layer0_repo,
            mock.MagicMock(),
            auth.NoopAuthenticator(),
            cls.clients,
        )

        cls._layer0_repo: repositories.Layer0Repository = layer0_repo
        cls._common_repo: repositories.CommonRepository = common_repo

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table_happy_case(self):
        self.clients.ads.query_simple.return_value = [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ]

        table_resp, _ = actions.create_table(
            self.depot,
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibcode="2024arXiv240411942F",
                datatype="regular",
                description="",
            ),
        )

        actions.add_data(
            self.depot,
            model.AddDataRequest(
                table_resp.id,
                data=[
                    {"test_col_1": 5.5, "test_col_2": "test data 1"},
                    {"test_col_1": 5.0, "test_col_2": "test data 2"},
                ],
            ),
        )

        rows = self.pg_storage.get_storage().query(
            "SELECT test_col_1, test_col_2 FROM rawdata.test_table ORDER BY test_col_1"
        )
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["test_col_1"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["test_col_2"].to_list(), ["test data 2", "test data 1"])

    def test_create_table_with_nulls(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ]
        )

        table_resp, _ = actions.create_table(
            self.depot,
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibcode="2024arXiv240411942F",
                datatype="regular",
                description="",
            ),
        )

        actions.add_data(
            self.depot,
            model.AddDataRequest(
                table_resp.id,
                data=[{"test_col_1": 5.5}, {"test_col_1": 5.0}],
            ),
        )

        rows = self.pg_storage.get_storage().query(
            "SELECT test_col_1, test_col_2 FROM rawdata.test_table ORDER BY test_col_1"
        )
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["test_col_1"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["test_col_2"].to_list(), [None, None])

    def test_duplicate_column(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ]
        )

        with self.assertRaises(psycopg.errors.DuplicateColumn):
            _ = actions.create_table(
                self.depot,
                model.CreateTableRequest(
                    "test_table",
                    [
                        model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                        model.ColumnDescription("test_col_1", "str", None, "test col 2"),
                    ],
                    bibcode="2024arXiv240411942F",
                    datatype="regular",
                    description="",
                ),
            )

    def test_add_data_to_unknown_column(self):
        self.clients.ads.query_simple = mock.MagicMock(
            return_value=[
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ]
        )

        table_resp, _ = actions.create_table(
            self.depot,
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibcode="2024arXiv240411942F",
                datatype="regular",
                description="",
            ),
        )

        with self.assertRaises(psycopg.errors.UndefinedColumn):
            actions.add_data(
                self.depot,
                model.AddDataRequest(
                    table_resp.id,
                    data=[{"totally_nonexistent_column": 5.5}],
                ),
            )

    def test_fetch_raw_table(self):
        data = DataFrame({"col0": [1, 2, 3, 4], "col1": ["ad", "ad", "a", "he"]})
        bib_id = self._common_repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
        table_id, _ = self._layer0_repo.create_table(
            Layer0Creation(
                "test_table",
                [ColumnDescription("col0", TYPE_INTEGER), ColumnDescription("col1", TYPE_TEXT)],
                bib_id,
                enums.DataType.REGULAR,
            ),
        )
        self._layer0_repo.insert_raw_data(Layer0RawData(table_id, data))
        from_db = self._layer0_repo.fetch_raw_data(table_id)

        self.assertTrue(from_db.data.equals(data))

        from_db = self._layer0_repo.fetch_raw_data(table_id, ["col1"])
        self.assertTrue(from_db.data.equals(data.drop(["col0"], axis=1)))

    def test_fetch_metadata(self):
        bib_id = self._common_repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
        table_name = "test_table"
        expected_creation = Layer0Creation(
            table_name,
            [ColumnDescription("col0", TYPE_INTEGER), ColumnDescription("col1", TYPE_TEXT)],
            bib_id,
            enums.DataType.REGULAR,
        )
        table_id, _ = self._layer0_repo.create_table(expected_creation)

        from_db = self._layer0_repo.fetch_metadata(table_id)

        self.assertEqual(expected_creation, from_db)
