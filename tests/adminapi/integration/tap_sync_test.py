import unittest

import psycopg
import structlog
from starlette import testclient

from app.adminapi import clients, domain
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.adminapi.presentation.server import Server
from app.data import repositories
from app.lib import audit, auth
from app.lib.web import server
from tests import lib


class AdminTapSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

    def setUp(self) -> None:
        pg = self.pg_storage.get_storage()
        log = structlog.get_logger()
        layer0_repo = repositories.Layer0Repository(pg, log)
        self.actions = domain.Actions(
            common_repo=repositories.CommonRepository(pg, log),
            layer0_repo=layer0_repo,
            layer1_repo=repositories.Layer1Repository(pg, log),
            layer2_repo=repositories.Layer2Repository(pg, log),
            metadata_repo=repositories.MetadataRepository(pg),
            authenticator=auth.NoopAuthenticator(),
            clients=clients.Clients(ads_token="test"),
            table_stats_cache=get_mock_table_stats_cache(),
        )
        cfg = server.ServerConfig(host="127.0.0.1", port=0, path_prefix="/admin/api")
        self.client = testclient.TestClient(
            Server(
                self.actions,
                cfg,
                log,
                auth.NoopAuthenticator(),
                audit.NoopActionRecorder(),
                auth_enabled=False,
            ).app
        )

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_tap_sync_basic(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": "SELECT type_name, objclass, description FROM nature.object_type ORDER BY type_name LIMIT 1",
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        col_names = [c["name"] for c in table["columns"]]
        self.assertEqual(col_names, ["type_name", "objclass", "description"])
        type_name_col = table["columns"][0]
        self.assertEqual(type_name_col["datatype"], "char")
        self.assertEqual(type_name_col["arraysize"], "*")
        self.assertEqual(len(table["data"]), 1)
        self.assertEqual(len(table["data"][0]), 3)

    def test_tap_sync_maxrec(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": "SELECT type_name FROM nature.object_type ORDER BY type_name",
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        self.assertEqual(len(table["data"]), 2)

    def test_tap_sync_maxrec_not_bypassed_by_line_comment(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": "SELECT type_name FROM nature.object_type ORDER BY type_name --",
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        self.assertEqual(len(table["data"]), 2)

    def test_tap_sync_maxrec_not_bypassed_by_unterminated_block_comment(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": ("SELECT type_name FROM nature.object_type ORDER BY type_name) AS _tap_sync LIMIT 10000 /*"),
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 500)

    def test_tap_sync_rejects_semicolon_separated_queries(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": (
                    "SELECT type_name FROM nature.object_type LIMIT 1; SELECT type_name FROM nature.object_type LIMIT 1"
                ),
            },
        )
        self.assertEqual(response.status_code, 500)

    def test_tap_sync_rejects_maxrec_over_500(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": "SELECT type_name FROM nature.object_type ORDER BY type_name",
                "maxrec": 501,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_tap_sync_rejects_insert(self) -> None:
        response = self.client.get(
            "/admin/api/v1/tap/sync",
            params={
                "query": (
                    "WITH inserted AS ("
                    "INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y') RETURNING *"
                    ") SELECT * FROM inserted"
                ),
            },
        )
        self.assertEqual(response.status_code, 500)

    def test_tap_sync_read_only_restored_for_writes(self) -> None:
        pg = self.pg_storage.get_storage()
        with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
            pg.query(
                "INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')",
                read_only=True,
            )
        pg.exec("INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')")
