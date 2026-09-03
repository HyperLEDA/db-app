import pytest
import structlog

from app.adminapi import clients, domain, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.lib.storage import enums
from app.specs import adminapi
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def upload_context(pg_storage: PostgresTestStorage) -> tuple[domain.SourceManager, domain.TableUploadManager]:
    repo = repository.Repository(pg_storage.get_storage(), structlog.get_logger())
    source_manager = domain.SourceManager(repo)
    upload_manager = domain.TableUploadManager(
        repo,
        clients.get_mock_clients(),
        get_mock_table_stats_cache(),
    )
    return source_manager, upload_manager


def test_create_table(upload_context: tuple) -> None:
    source_manager, upload_manager = upload_context
    source_code = source_manager.create_source(
        adminapi.CreateSourceRequest(title="title", authors=["author"], year=2022)
    ).code

    upload_manager.create_table(
        adminapi.CreateTableRequest(
            table_name="table_name",
            columns=[
                adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["text"], ucd="meta.id"),
                adminapi.ColumnDescription(
                    name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="rad"
                ),
                adminapi.ColumnDescription(
                    name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                ),
                adminapi.ColumnDescription(
                    name="redshift", data_type=adminapi.DatatypeEnum["float"], ucd="src.redshift"
                ),
            ],
            bibcode=source_code,
            datatype=enums.DataType.REGULAR,
            description="description",
        )
    )


def test_create_table_with_patch(upload_context: tuple) -> None:
    source_manager, upload_manager = upload_context
    source_code = source_manager.create_source(
        adminapi.CreateSourceRequest(title="title", authors=["author"], year=2022)
    ).code
    table_name = "table_name"

    _, created = upload_manager.create_table(
        adminapi.CreateTableRequest(
            table_name=table_name,
            columns=[
                adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["text"]),
                adminapi.ColumnDescription(name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra"),
                adminapi.ColumnDescription(
                    name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="rad"
                ),
            ],
            bibcode=source_code,
            datatype=enums.DataType.REGULAR,
            description="description",
        )
    )

    assert created

    upload_manager.patch_table(
        adminapi.PatchTableRequest(
            table_name=table_name,
            description="updated table description",
            datatype=enums.DataType.PRELIMINARY,
            columns={
                "name": adminapi.PatchColumnSpec(ucd="meta.id"),
                "ra": adminapi.PatchColumnSpec(unit="hourangle"),
            },
        ),
    )

    meta = upload_manager.get_table(adminapi.GetTableRequest(table_name=table_name))
    assert meta.description == "updated table description"
    assert meta.meta["datatype"] == enums.DataType.PRELIMINARY
    assert meta.meta["status"] == enums.TableStatus.INITIATED

    upload_manager.patch_table(
        adminapi.PatchTableRequest(
            table_name=table_name,
            status=enums.TableStatus.ARCHIVED,
        ),
    )

    meta = upload_manager.get_table(adminapi.GetTableRequest(table_name=table_name))
    assert meta.meta["status"] == enums.TableStatus.ARCHIVED

    default_list = upload_manager.get_table_list(adminapi.GetTableListRequest(query=table_name))
    assert default_list.tables == []

    archived_list = upload_manager.get_table_list(
        adminapi.GetTableListRequest(
            query=table_name,
            statuses=[enums.TableStatus.ARCHIVED],
        )
    )
    assert len(archived_list.tables) == 1
    assert archived_list.tables[0].name == table_name
    assert archived_list.tables[0].status == enums.TableStatus.ARCHIVED
