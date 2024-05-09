import unittest

import pandas
import structlog
from pandas import DataFrame

from app.data import repositories
from app.data.model import Bibliography
from app.data.model.layer0 import ColumnDescription, Layer0Creation, Layer0RawData
from app.domain import model, usecases
from app.lib import auth, exceptions, testing
from app.lib.storage import enums
from app.lib.storage.mapping import TYPE_INTEGER, TYPE_TEXT


class RawDataTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        logger = structlog.get_logger()

        cls.actions = usecases.Actions(
            common_repo=repositories.CommonRepository(cls.pg_storage.get_storage(), logger),
            layer0_repo=repositories.Layer0Repository(cls.pg_storage.get_storage(), logger),
            layer1_repo=repositories.Layer1Repository(cls.pg_storage.get_storage(), logger),
            queue_repo=None,
            authenticator=auth.NoopAuthenticator(),
            storage_config=None,
            logger=logger,
        )

        cls._layer0_repo: repositories.Layer0Repository = layer0_repo
        cls._common_repo: repositories.CommonRepository = common_repo

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table_happy_case(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        table_resp = self.actions.create_table(
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibliography_id=bib_resp.id,
                datatype="regular",
                description="",
            )
        )

        self.actions.add_data(
            model.AddDataRequest(
                table_resp.id,
                data=[
                    {"test_col_1": 5.5, "test_col_2": "test data 1"},
                    {"test_col_1": 5.0, "test_col_2": "test data 2"},
                ],
            )
        )

        rows = self.pg_storage.get_storage().query(
            "SELECT test_col_1, test_col_2 FROM rawdata.test_table ORDER BY test_col_1"
        )
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["test_col_1"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["test_col_2"].to_list(), ["test data 2", "test data 1"])

    def test_create_table_with_nulls(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        table_resp = self.actions.create_table(
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibliography_id=bib_resp.id,
                datatype="regular",
                description="",
            )
        )

        self.actions.add_data(
            model.AddDataRequest(
                table_resp.id,
                data=[{"test_col_1": 5.5}, {"test_col_1": 5.0}],
            )
        )

        rows = self.pg_storage.get_storage().query(
            "SELECT test_col_1, test_col_2 FROM rawdata.test_table ORDER BY test_col_1"
        )
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["test_col_1"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["test_col_2"].to_list(), [None, None])

    def test_unknown_bibliograhy(self):
        with self.assertRaises(exceptions.APIException):
            _ = self.actions.create_table(
                model.CreateTableRequest(
                    "test_table",
                    [
                        model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                        model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                    ],
                    bibliography_id=123456,
                    datatype="regular",
                    description="",
                )
            )

            # TODO: check that status code is 400

    def test_duplicate_column(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        with self.assertRaises(exceptions.APIException):
            _ = self.actions.create_table(
                model.CreateTableRequest(
                    "test_table",
                    [
                        model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                        model.ColumnDescription("test_col_1", "str", None, "test col 2"),
                    ],
                    bibliography_id=bib_resp.id,
                    datatype="regular",
                    description="",
                )
            )

            # TODO: check that status code is 400

    def test_unknown_data_type(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        with self.assertRaises(exceptions.APIException) as ctx:
            _ = self.actions.create_table(
                model.CreateTableRequest(
                    "test_table",
                    [
                        model.ColumnDescription("test_col_1", "totally_real_type", "kpc", "test col 1"),
                        model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                    ],
                    bibliography_id=bib_resp.id,
                    datatype="regular",
                    description="",
                )
            )

            self.assertEqual(ctx.exception.status, 400)

    def test_add_data_to_unknown_column(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        table_resp = self.actions.create_table(
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibliography_id=bib_resp.id,
                datatype="regular",
                description="",
            )
        )

        with self.assertRaises(exceptions.APIException):
            self.actions.add_data(
                model.AddDataRequest(
                    table_resp.id,
                    data=[{"totally_nonexistent_column": 5.5}],
                )
            )

    def test_duplicate_table(self):
        bib_resp = self.actions.create_source(model.CreateSourceRequest("2024arXiv240411942F", "test", ["test"], 2020))

        _ = self.actions.create_table(
            model.CreateTableRequest(
                "test_table",
                [
                    model.ColumnDescription("test_col_1", "float", "kpc", "test col 1"),
                    model.ColumnDescription("test_col_2", "str", None, "test col 2"),
                ],
                bibliography_id=bib_resp.id,
                datatype="regular",
                description="",
            )
        )

        with self.assertRaises(exceptions.APIException):
            _ = self.actions.create_table(
                model.CreateTableRequest(
                    "test_table",
                    [model.ColumnDescription("test_col_1", "float", "kpc", "test col 1")],
                    bibliography_id=bib_resp.id,
                    datatype="regular",
                    description="",
                )
            )

    def test_fetch_raw_table(self):
        data = DataFrame({"col0": [1, 2, 3, 4], "col1": ["ad", "ad", "a", "he"]})
        bib_id = self._common_repo.create_bibliography(Bibliography("2024arXiv240411942F", 1999, ["ade"], "title"))
        table_id = self._layer0_repo.create_table(
            Layer0Creation(
                "test_table",
                [ColumnDescription("col0", TYPE_INTEGER), ColumnDescription("col1", TYPE_TEXT)],
                bib_id,
                enums.DataType.REGULAR,
            )
        )
        self._layer0_repo.insert_raw_data(Layer0RawData(table_id, data))
        from_db = self._layer0_repo.fetch_raw_data(table_id)

        self.assertTrue(from_db.data.equals(data))

        from_db = self._layer0_repo.fetch_raw_data(table_id, ["col1"])
        self.assertTrue(from_db.data.equals(data.drop(["col0"], axis=1)))

    def test_fetch_metadata(self):
        bib_id = self._common_repo.create_bibliography(Bibliography("2024arXiv240411942F", 1999, ["ade"], "title"))
        table_name = "test_table"
        expected_creation = Layer0Creation(
            table_name,
            [ColumnDescription("col0", TYPE_INTEGER), ColumnDescription("col1", TYPE_TEXT)],
            bib_id,
            enums.DataType.REGULAR,
        )
        table_id = self._layer0_repo.create_table(expected_creation)

        from_db = self._layer0_repo.fetch_metadata(table_id)

        self.assertEqual(expected_creation, from_db)
