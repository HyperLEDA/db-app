import unittest

import pandas
import psycopg
import structlog
from pandas import DataFrame

from app.data import model, repositories
from app.domain import adminapi as domain
from app.lib import clients
from app.lib.storage import enums
from app.lib.storage.mapping import TYPE_INTEGER, TYPE_TEXT
from app.presentation import adminapi as presentation
from tests import lib


class RawDataTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

        cls.manager = domain.TableUploadManager(
            repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger()),
            repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger()),
            clients.get_mock_clients(),
        )

    def tearDown(self):
        self.pg_storage.clear()

    def test_create_table_happy_case(self):
        lib.returns(
            self.manager.clients.ads.query_simple,
            [
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ],
        )

        table_resp, _ = self.manager.create_table(
            presentation.CreateTableRequest(
                table_name="test_table",
                columns=[
                    presentation.ColumnDescription(
                        name="objname", data_type=presentation.DatatypeEnum["str"], ucd="meta.id"
                    ),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                    ),
                ],
                bibcode="2024arXiv240411942F",
                datatype=enums.DataType.REGULAR,
                description="",
            ),
        )

        self.manager.add_data(
            presentation.AddDataRequest(
                table_name="test_table",
                data=[
                    {"ra": 5.5, "dec": 88},
                    {"ra": 5.0, "dec": -50},
                ],
            ),
        )

        rows = self.pg_storage.get_storage().query("SELECT ra, dec FROM rawdata.test_table ORDER BY ra")
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["ra"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["dec"].to_list(), [-50, 88])

    def test_create_table_with_nulls(self):
        lib.returns(
            self.manager.clients.ads.query_simple,
            [
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ],
        )

        table_resp, _ = self.manager.create_table(
            presentation.CreateTableRequest(
                table_name="test_table",
                columns=[
                    presentation.ColumnDescription(
                        name="objname", data_type=presentation.DatatypeEnum["str"], ucd="meta.id"
                    ),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                    ),
                ],
                bibcode="2024arXiv240411942F",
                datatype=enums.DataType.REGULAR,
                description="",
            ),
        )

        self.manager.add_data(
            presentation.AddDataRequest(
                table_name="test_table",
                data=[{"ra": 5.5}, {"ra": 5.0}],
            ),
        )

        rows = self.pg_storage.get_storage().query("SELECT ra, dec FROM rawdata.test_table ORDER BY ra")
        data_df = pandas.DataFrame.from_records(rows)
        self.assertListEqual(data_df["ra"].to_list(), [5.0, 5.5])
        self.assertListEqual(data_df["dec"].to_list(), [None, None])

    def test_duplicate_column(self):
        lib.returns(
            self.manager.clients.ads.query_simple,
            [
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ],
        )

        with self.assertRaises(psycopg.errors.DuplicateColumn):
            _ = self.manager.create_table(
                presentation.CreateTableRequest(
                    table_name="test_table",
                    columns=[
                        presentation.ColumnDescription(
                            name="objname", data_type=presentation.DatatypeEnum["str"], ucd="meta.id"
                        ),
                        presentation.ColumnDescription(
                            name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                        ),
                        presentation.ColumnDescription(
                            name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                        ),
                        presentation.ColumnDescription(name="duplicate", data_type=presentation.DatatypeEnum["str"]),
                        presentation.ColumnDescription(name="duplicate", data_type=presentation.DatatypeEnum["str"]),
                    ],
                    bibcode="2024arXiv240411942F",
                    datatype=enums.DataType.REGULAR,
                    description="",
                ),
            )

    def test_add_data_to_unknown_column(self):
        lib.returns(
            self.manager.clients.ads.query_simple,
            [
                {
                    "bibcode": "2024arXiv240411942F",
                    "author": ["test"],
                    "pubdate": "2020-03-00",
                    "title": ["test"],
                }
            ],
        )

        table_resp, _ = self.manager.create_table(
            presentation.CreateTableRequest(
                table_name="test_table",
                columns=[
                    presentation.ColumnDescription(
                        name="objname", data_type=presentation.DatatypeEnum["str"], ucd="meta.id"
                    ),
                    presentation.ColumnDescription(
                        name="ra", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                    ),
                    presentation.ColumnDescription(
                        name="dec", data_type=presentation.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                    ),
                ],
                bibcode="2024arXiv240411942F",
                datatype=enums.DataType.REGULAR,
                description="",
            ),
        )

        with self.assertRaises(psycopg.errors.UndefinedColumn):
            self.manager.add_data(
                presentation.AddDataRequest(
                    table_name="test_table",
                    data=[{"totally_nonexistent_column": 5.5}],
                ),
            )

    def test_fetch_raw_table(self):
        data = DataFrame({"col0": [1, 2, 3, 4], "col1": ["ad", "ad", "a", "he"]})
        bib_id = self.manager.common_repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
        _ = self.manager.layer0_repo.create_table(
            model.Layer0TableMeta(
                "test_table",
                [model.ColumnDescription("col0", TYPE_INTEGER), model.ColumnDescription("col1", TYPE_TEXT)],
                bib_id,
                enums.DataType.REGULAR,
            ),
        )
        self.manager.layer0_repo.insert_raw_data(model.Layer0RawData("test_table", data))
        expected = self.manager.layer0_repo.fetch_raw_data("test_table")

        self.assertTrue(expected.data.equals(data))

        expected = self.manager.layer0_repo.fetch_raw_data("test_table", columns=["col1"])
        self.assertTrue(expected.data.equals(data.drop(["col0"], axis=1)))

    def test_fetch_metadata(self):
        bib_id = self.manager.common_repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
        table_name = "test_table"
        expected = model.Layer0TableMeta(
            table_name,
            [model.ColumnDescription("col0", TYPE_INTEGER), model.ColumnDescription("col1", TYPE_TEXT)],
            bib_id,
            enums.DataType.REGULAR,
        )
        _ = self.manager.layer0_repo.create_table(expected)

        actual = self.manager.layer0_repo.fetch_metadata("test_table")

        self.assertEqual(expected.table_name, actual.table_name)
        self.assertEqual(expected.column_descriptions, actual.column_descriptions)
        self.assertEqual(expected.bibliography_id, actual.bibliography_id)
        self.assertEqual(expected.datatype, actual.datatype)
