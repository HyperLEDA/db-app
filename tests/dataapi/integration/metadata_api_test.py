import pathlib
from collections.abc import Generator

import psycopg
import pytest
import structlog
from starlette import testclient

import app.dataapi.command as dataapi_command
from app.dataapi import clients, domain, repository
from app.dataapi.domain import actions as dataapi_actions
from app.dataapi.presentation.server import Server
from app.lib import mock
from app.lib.storage import enums, postgres
from tests.lib.postgres import TestPostgresStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def dataapi_config() -> dataapi_command.Config:
    cfg_path = pathlib.Path(__file__).resolve().parents[3] / "configs" / "dev" / "dataapi.yaml"
    return dataapi_command.parse_config(str(cfg_path))


@pytest.fixture(scope="module")
def log() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()


@pytest.fixture(scope="module")
def reader_storage(pg_storage: TestPostgresStorage, log: structlog.stdlib.BoundLogger) -> Generator[postgres.PgStorage]:
    reader_config = postgres.PgStorageConfig(
        endpoint=pg_storage.config.endpoint,
        port=pg_storage.config.port,
        user="hyperleda_reader",
        password="password",
        dbname=pg_storage.config.dbname,
    )
    storage = postgres.PgStorage(reader_config, log, enums.PG_ENUM_REGISTRY)
    storage.connect()
    yield storage
    storage.disconnect()


@pytest.fixture
def client(
    reader_storage: postgres.PgStorage,
    dataapi_config: dataapi_command.Config,
    log: structlog.stdlib.BoundLogger,
) -> testclient.TestClient:
    actions = domain.Actions(
        repo=repository.Repository(reader_storage, log),
        catalog_cfg=dataapi_config.catalogs,
        fieldapi_client=mock.create_autospec(clients.FieldAPIClient),
    )
    return testclient.TestClient(Server(actions, dataapi_config.server, log).app)


def test_tap_tables_default_max(client: testclient.TestClient) -> None:
    response = client.get("/api/v1/tap/tables")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "schemas" in data
    assert len(data["schemas"]) > 0
    common = next(s for s in data["schemas"] if s["schema_name"] == "common")
    bib = next(t for t in common["tables"] if t["name"] == 'common."bib"')
    assert bib["type"] == "table"
    assert "columns" in bib
    assert isinstance(bib["columns"], list)
    assert len(bib["columns"]) > 0
    id_col = next(c for c in bib["columns"] if c["name"] == "id")
    assert id_col["datatype"] == "int"


def test_tap_tables_min(client: testclient.TestClient) -> None:
    response = client.get("/api/v1/tap/tables", params={"detail": "min"})
    assert response.status_code == 200
    for schema in response.json()["data"]["schemas"]:
        for table in schema["tables"]:
            assert "columns" not in table


def test_tap_tables_whitelist(client: testclient.TestClient) -> None:
    response = client.get("/api/v1/tap/tables")
    assert response.status_code == 200
    table_names: set[str] = set()
    for schema in response.json()["data"]["schemas"]:
        assert schema["schema_name"] in dataapi_actions.METADATA_ALLOWED_SCHEMAS
        table_names.update(t["name"] for t in schema["tables"])
    assert 'common."users"' not in table_names
    assert 'common."tokens"' not in table_names


def test_tap_sync_basic(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": "SELECT type_name, objclass, description FROM nature.object_type ORDER BY type_name LIMIT 1",
        },
    )
    assert response.status_code == 200
    table = response.json()["data"]["resource"]["table"]
    col_names = [c["name"] for c in table["columns"]]
    assert col_names == ["type_name", "objclass", "description"]
    type_name_col = table["columns"][0]
    assert type_name_col["datatype"] == "char"
    assert type_name_col["arraysize"] == "*"
    assert len(table["data"]) == 1
    assert len(table["data"][0]) == 3


def test_tap_sync_maxrec(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": "SELECT type_name FROM nature.object_type ORDER BY type_name",
            "maxrec": 2,
        },
    )
    assert response.status_code == 200
    table = response.json()["data"]["resource"]["table"]
    assert len(table["data"]) == 2


def test_tap_sync_maxrec_not_bypassed_by_line_comment(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": "SELECT type_name FROM nature.object_type ORDER BY type_name --",
            "maxrec": 2,
        },
    )
    assert response.status_code == 200
    table = response.json()["data"]["resource"]["table"]
    assert len(table["data"]) == 2


def test_tap_sync_maxrec_not_bypassed_by_unterminated_block_comment(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": ("SELECT type_name FROM nature.object_type ORDER BY type_name) AS _tap_sync LIMIT 10000 /*"),
            "maxrec": 2,
        },
    )
    assert response.status_code == 500


def test_tap_sync_rejects_semicolon_separated_queries(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": (
                "SELECT type_name FROM nature.object_type LIMIT 1; SELECT type_name FROM nature.object_type LIMIT 1"
            ),
        },
    )
    assert response.status_code == 500


def test_tap_sync_like_with_percent_wildcard(client: testclient.TestClient) -> None:
    response = client.get(
        "/api/v1/tap/sync",
        params={
            "query": "SELECT type_name FROM nature.object_type WHERE type_name NOT LIKE '%gal%'",
        },
    )
    assert response.status_code == 200
    table = response.json()["data"]["resource"]["table"]
    assert [c["name"] for c in table["columns"]] == ["type_name"]
    assert all("gal" not in row[0].lower() for row in table["data"])


def test_tap_sync_query_timeout(pg_storage: TestPostgresStorage) -> None:
    pg = pg_storage.get_storage()
    with pytest.raises(psycopg.errors.QueryCanceled):
        pg.query("SELECT pg_sleep(2)", timeout_seconds=1)


def test_reader_cannot_write(reader_storage: postgres.PgStorage) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader_storage.exec("INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')")
