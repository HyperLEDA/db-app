import pandas
import psycopg
import pytest
import structlog
from pandas import DataFrame

from app.adminapi import clients, domain, model, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.lib.storage import enums, postgres
from app.lib.storage.mapping import TYPE_INTEGER, TYPE_TEXT
from app.lib.web import errors
from app.specs import adminapi
from tests import lib
from tests.lib.postgres import TestPostgresStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: TestPostgresStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture(scope="module")
def manager(pg_storage: TestPostgresStorage) -> domain.TableUploadManager:
    repo = repository.Repository(pg_storage.get_storage(), structlog.get_logger())
    return domain.TableUploadManager(
        repo,
        clients.get_mock_clients(),
        get_mock_table_stats_cache(),
    )


def test_create_table_happy_case(manager: domain.TableUploadManager, pg_storage: TestPostgresStorage) -> None:
    lib.returns(
        manager.clients.ads.query_simple,
        [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ],
    )

    manager.create_table(
        adminapi.CreateTableRequest(
            table_name="test_table",
            columns=[
                adminapi.ColumnDescription(name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"),
                adminapi.ColumnDescription(
                    name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                ),
                adminapi.ColumnDescription(
                    name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                ),
            ],
            bibcode="2024arXiv240411942F",
            datatype=enums.DataType.REGULAR,
            description="",
        ),
    )

    manager.add_data(
        adminapi.AddDataRequest(
            table_name="test_table",
            data=[
                {"ra": 5.5, "dec": 88},
                {"ra": 5.0, "dec": -50},
            ],
        ),
    )

    rows = pg_storage.get_storage().query("SELECT ra, dec FROM rawdata.test_table ORDER BY ra")
    data_df = pandas.DataFrame.from_records(rows)
    assert data_df["ra"].to_list() == [5.0, 5.5]
    assert data_df["dec"].to_list() == [-50, 88]


def test_create_table_with_nulls(manager: domain.TableUploadManager, pg_storage: TestPostgresStorage) -> None:
    lib.returns(
        manager.clients.ads.query_simple,
        [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ],
    )

    manager.create_table(
        adminapi.CreateTableRequest(
            table_name="test_table",
            columns=[
                adminapi.ColumnDescription(name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"),
                adminapi.ColumnDescription(
                    name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                ),
                adminapi.ColumnDescription(
                    name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                ),
            ],
            bibcode="2024arXiv240411942F",
            datatype=enums.DataType.REGULAR,
            description="",
        ),
    )

    manager.add_data(
        adminapi.AddDataRequest(
            table_name="test_table",
            data=[{"ra": 5.5}, {"ra": 5.0}],
        ),
    )

    rows = pg_storage.get_storage().query("SELECT ra, dec FROM rawdata.test_table ORDER BY ra")
    data_df = pandas.DataFrame.from_records(rows)
    assert data_df["ra"].to_list() == [5.0, 5.5]
    assert data_df["dec"].to_list() == [None, None]


def test_duplicate_column(manager: domain.TableUploadManager) -> None:
    lib.returns(
        manager.clients.ads.query_simple,
        [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ],
    )

    with pytest.raises(errors.RuleValidationError):
        _ = manager.create_table(
            adminapi.CreateTableRequest(
                table_name="test_table",
                columns=[
                    adminapi.ColumnDescription(name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"),
                    adminapi.ColumnDescription(
                        name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                    ),
                    adminapi.ColumnDescription(
                        name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                    ),
                    adminapi.ColumnDescription(name="duplicate", data_type=adminapi.DatatypeEnum["str"]),
                    adminapi.ColumnDescription(name="duplicate", data_type=adminapi.DatatypeEnum["str"]),
                ],
                bibcode="2024arXiv240411942F",
                datatype=enums.DataType.REGULAR,
                description="",
            ),
        )


def test_add_data_to_unknown_column(manager: domain.TableUploadManager) -> None:
    lib.returns(
        manager.clients.ads.query_simple,
        [
            {
                "bibcode": "2024arXiv240411942F",
                "author": ["test"],
                "pubdate": "2020-03-00",
                "title": ["test"],
            }
        ],
    )

    manager.create_table(
        adminapi.CreateTableRequest(
            table_name="test_table",
            columns=[
                adminapi.ColumnDescription(name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"),
                adminapi.ColumnDescription(
                    name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                ),
                adminapi.ColumnDescription(
                    name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                ),
            ],
            bibcode="2024arXiv240411942F",
            datatype=enums.DataType.REGULAR,
            description="",
        ),
    )

    with pytest.raises(psycopg.errors.UndefinedColumn):
        manager.add_data(
            adminapi.AddDataRequest(
                table_name="test_table",
                data=[{"totally_nonexistent_column": 5.5}],
            ),
        )


def test_fetch_raw_table(repo: repository.Repository) -> None:
    data = DataFrame({"col0": [1, 2, 3, 4], "col1": ["ad", "ad", "a", "he"]})
    bib_id = repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
    _ = repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test_table",
                columns={
                    "col0": postgres.ColumnInfo("col0", TYPE_INTEGER),
                    "col1": postgres.ColumnInfo("col1", TYPE_TEXT),
                },
            ),
            bib_id,
            enums.DataType.REGULAR,
        ),
    )
    repo.insert_raw_data(model.Layer0RawData("test_table", data))
    expected = repo.fetch_raw_data("test_table")

    assert expected.data.equals(data)

    expected = repo.fetch_raw_data("test_table", columns=["col1"])
    assert expected.data.equals(data.drop(["col0"], axis=1))


def test_fetch_metadata(repo: repository.Repository) -> None:
    bib_id = repo.create_bibliography("2024arXiv240411942F", 1999, ["ade"], "title")
    table_name = "test_table"
    expected = model.Layer0TableMeta(
        postgres.TableInfo(
            schema=repository.RAWDATA_SCHEMA,
            name=table_name,
            columns={
                "col0": postgres.ColumnInfo("col0", TYPE_INTEGER),
                "col1": postgres.ColumnInfo("col1", TYPE_TEXT),
            },
        ),
        bib_id,
        enums.DataType.REGULAR,
    )
    _ = repo.create_table(expected)

    actual = repo.fetch_metadata("test_table")

    assert expected.table_info.name == actual.table_info.name
    assert expected.table_info.columns == actual.table_info.columns
    assert expected.bibliography_id == actual.bibliography_id
    assert expected.datatype == actual.datatype
