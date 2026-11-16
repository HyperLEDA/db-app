from unittest import mock

import pytest
import structlog

from app.adminapi import clients, domain, repository
from app.adminapi.domain import layer1_write
from app.adminapi.repository.layer0 import tables
from app.lib.storage import enums
from app.specs import adminapi
from tests import lib
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")

TABLE_NAME = "preview_table"
ROW_COUNT = 200


@pytest.fixture
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture
def raw_table(repo: repository.Repository) -> str:
    mock_clients = clients.get_mock_clients()
    lib.returns(
        mock_clients.ads.query_simple,
        [{"bibcode": "2024arXiv240411942F", "author": ["test"], "pubdate": "2020-03-00", "title": ["test"]}],
    )
    manager = domain.TableUploadManager(repo, mock_clients)
    manager.create_table(
        adminapi.CreateTableRequest(
            table_name=TABLE_NAME,
            columns=[
                adminapi.ColumnDescription(name="ra", data_type=adminapi.DatatypeEnum["float"], unit="deg"),
                adminapi.ColumnDescription(name="dec", data_type=adminapi.DatatypeEnum["float"], unit="deg"),
                adminapi.ColumnDescription(name="type", data_type=adminapi.DatatypeEnum["str"]),
            ],
            bibcode="2024arXiv240411942F",
            datatype=enums.DataType.REGULAR,
            description="",
        )
    )
    manager.add_data(
        adminapi.AddDataRequest(
            table_name=TABLE_NAME,
            data=[
                {"ra": float(i % 360), "dec": None if i % 10 == 0 else float(i % 90), "type": "G"}
                for i in range(ROW_COUNT)
            ],
        )
    )
    return TABLE_NAME


def test_sample_rawdata_small_table(repo: repository.Repository, raw_table: str) -> None:
    rows = repo.sample_rawdata(raw_table, ["ra", "dec"], 5)

    assert len(rows) == 5
    assert all(set(row) == {"hyperleda_internal_id", "ra", "dec"} for row in rows)
    assert len({row["hyperleda_internal_id"] for row in rows}) == 5


def test_sample_rawdata_tablesample(
    repo: repository.Repository, raw_table: str, pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    pg_storage.get_storage().exec(f'ANALYZE rawdata."{raw_table}"')
    monkeypatch.setattr(tables, "_TABLESAMPLE_MIN_ROWS_PER_LIMIT", 1)

    rows = repo.sample_rawdata(raw_table, ["ra", "type"], 5)

    assert len(rows) == 5
    assert all(set(row) == {"hyperleda_internal_id", "ra", "type"} for row in rows)


def test_sample_rawdata_unanalyzed_table_uses_small_path(
    repo: repository.Repository, raw_table: str, pg_storage: PostgresTestStorage
) -> None:
    estimate = pg_storage.get_storage().query_one(
        "SELECT reltuples FROM pg_class WHERE oid = to_regclass(%s)", params=[f"rawdata.{raw_table}"]
    )
    assert estimate["reltuples"] <= 0

    assert len(repo.sample_rawdata(raw_table, ["ra"], 3)) == 3


def test_preview_upload_end_to_end(repo: repository.Repository, raw_table: str) -> None:
    writer = layer1_write.Layer1Writer(repo, mock.Mock())

    response = writer.preview_upload(
        adminapi.PreviewStructuredUploadRequest(
            catalog="icrs",
            table_name=raw_table,
            limit=200,
            expressions={
                "ra": 'col("ra")',
                "dec": 'col("dec")',
                "e_ra": 'col("missing")',
                "e_dec": "1 +",
            },
        )
    )

    assert len(response.rows) == ROW_COUNT
    skipped = [row for row in response.rows if row.skipped_reason is not None]
    assert len(skipped) == ROW_COUNT // 10
    assert all(row.skipped_reason == "null in dec" for row in skipped)
    computed = [row for row in response.rows if row.skipped_reason is None]
    assert all(set(row.outputs) == {"ra", "dec"} for row in computed)
    assert {error.field for error in response.errors} == {"e_ra", "e_dec"}
    response.model_dump_json()


def test_preview_upload_text_expression(repo: repository.Repository, raw_table: str) -> None:
    writer = layer1_write.Layer1Writer(repo, mock.Mock())

    response = writer.preview_upload(
        adminapi.PreviewStructuredUploadRequest(
            catalog="designation",
            table_name=raw_table,
            limit=3,
            expressions={"design": '"SDSS J" + zfill(str(floor(col("ra") / deg / 15)), 2)'},
        )
    )

    assert not response.errors
    assert len(response.rows) == 3
    assert all(str(row.outputs["design"]).startswith("SDSS J") for row in response.rows)
