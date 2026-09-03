import psycopg
import pytest
import structlog
from starlette import testclient

from app.adminapi import clients, domain, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.adminapi.presentation.server import Server
from app.lib import audit, auth
from app.lib.web import server
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture
def client(cleared_pg_storage: PostgresTestStorage) -> testclient.TestClient:
    pg = cleared_pg_storage.get_storage()
    log = structlog.get_logger()
    actions = domain.Actions(
        repo=repository.Repository(pg, log),
        authenticator=auth.NoopAuthenticator(),
        storage=pg,
        clients=clients.Clients(ads_token="test"),
        table_stats_cache=get_mock_table_stats_cache(),
    )
    cfg = server.ServerConfig(host="127.0.0.1", port=0, path_prefix="/admin/api")
    return testclient.TestClient(
        Server(
            actions,
            cfg,
            log,
            auth.NoopAuthenticator(),
            audit.NoopActionRecorder(),
            auth_enabled=False,
        ).app
    )


def test_tap_sync_basic(client: testclient.TestClient) -> None:
    response = client.get(
        "/admin/api/v1/tap/sync",
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
        "/admin/api/v1/tap/sync",
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
        "/admin/api/v1/tap/sync",
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
        "/admin/api/v1/tap/sync",
        params={
            "query": ("SELECT type_name FROM nature.object_type ORDER BY type_name) AS _tap_sync LIMIT 10000 /*"),
            "maxrec": 2,
        },
    )
    assert response.status_code == 500


def test_tap_sync_rejects_semicolon_separated_queries(client: testclient.TestClient) -> None:
    response = client.get(
        "/admin/api/v1/tap/sync",
        params={
            "query": (
                "SELECT type_name FROM nature.object_type LIMIT 1; SELECT type_name FROM nature.object_type LIMIT 1"
            ),
        },
    )
    assert response.status_code == 500


def test_tap_sync_rejects_maxrec_over_500(client: testclient.TestClient) -> None:
    response = client.get(
        "/admin/api/v1/tap/sync",
        params={
            "query": "SELECT type_name FROM nature.object_type ORDER BY type_name",
            "maxrec": 501,
        },
    )
    assert response.status_code == 400


def test_tap_sync_rejects_insert(client: testclient.TestClient) -> None:
    response = client.get(
        "/admin/api/v1/tap/sync",
        params={
            "query": (
                "WITH inserted AS ("
                "INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y') RETURNING *"
                ") SELECT * FROM inserted"
            ),
        },
    )
    assert response.status_code == 500


def test_tap_sync_read_only_restored_for_writes(pg_storage: PostgresTestStorage) -> None:
    pg = pg_storage.get_storage()
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        pg.query(
            "INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')",
            read_only=True,
        )
    pg.exec("INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')")
