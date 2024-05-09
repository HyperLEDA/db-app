import unittest

import pandas
import structlog

from app.data import repositories
from app.domain import model, usecases
from app.lib import auth, exceptions, testing


class RawDataTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

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
