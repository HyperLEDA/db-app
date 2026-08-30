import pathlib
import unittest
from unittest import mock

import psycopg
import structlog
from starlette import testclient

import app.dataapi.command as dataapi_command
from app.dataapi import clients, domain, repository
from app.dataapi.domain import actions as dataapi_actions
from app.dataapi.presentation.server import Server
from app.lib.storage import enums, postgres
from tests import lib


class MetadataAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)
        cfg_path = pathlib.Path(__file__).resolve().parents[3] / "configs" / "dev" / "dataapi.yaml"
        cls.cfg = dataapi_command.parse_config(str(cfg_path))
        cls.log = structlog.get_logger()

        reader_config = postgres.PgStorageConfig(
            endpoint=cls.pg_storage.config.endpoint,
            port=cls.pg_storage.config.port,
            user="hyperleda_reader",
            password="password",
            dbname=cls.pg_storage.config.dbname,
        )
        cls.reader_storage = postgres.PgStorage(reader_config, cls.log, enums.PG_ENUM_REGISTRY)
        cls.reader_storage.connect()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.reader_storage.disconnect()

    def setUp(self) -> None:
        self.pg = self.pg_storage.get_storage()
        self.actions = domain.Actions(
            repo=repository.Repository(self.reader_storage, self.log),
            catalog_cfg=self.cfg.catalogs,
            fieldapi_client=mock.create_autospec(clients.FieldAPIClient),
        )
        self.client = testclient.TestClient(Server(self.actions, self.cfg.server, self.log).app)

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_tap_tables_default_max(self) -> None:
        response = self.client.get("/api/v1/tap/tables")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("schemas", data)
        self.assertGreater(len(data["schemas"]), 0)
        layer2 = next(s for s in data["schemas"] if s["schema_name"] == "layer2")
        icrs = next(t for t in layer2["tables"] if t["name"] == 'layer2."icrs"')
        self.assertEqual(icrs["type"], "table")
        self.assertIn("columns", icrs)
        self.assertIsInstance(icrs["columns"], list)
        self.assertGreater(len(icrs["columns"]), 0)
        pgc_col = next(c for c in icrs["columns"] if c["name"] == "pgc")
        self.assertEqual(pgc_col["datatype"], "int")

    def test_tap_tables_min(self) -> None:
        response = self.client.get("/api/v1/tap/tables", params={"detail": "min"})
        self.assertEqual(response.status_code, 200)
        for schema in response.json()["data"]["schemas"]:
            for table in schema["tables"]:
                self.assertNotIn("columns", table)

    def test_tap_tables_whitelist(self) -> None:
        response = self.client.get("/api/v1/tap/tables")
        self.assertEqual(response.status_code, 200)
        table_names: set[str] = set()
        for schema in response.json()["data"]["schemas"]:
            self.assertIn(schema["schema_name"], dataapi_actions.METADATA_ALLOWED_SCHEMAS)
            table_names.update(t["name"] for t in schema["tables"])
        self.assertNotIn('common."users"', table_names)
        self.assertNotIn('common."tokens"', table_names)

    def test_tap_sync_basic(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": "SELECT catalog FROM last_update ORDER BY catalog LIMIT 1",
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        col_names = [c["name"] for c in table["columns"]]
        self.assertEqual(col_names, ["catalog"])
        catalog_col = table["columns"][0]
        self.assertEqual(catalog_col["datatype"], "char")
        self.assertEqual(catalog_col["arraysize"], "*")
        self.assertEqual(len(table["data"]), 1)
        self.assertEqual(len(table["data"][0]), 1)

    def test_tap_sync_maxrec(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": "SELECT catalog FROM last_update ORDER BY catalog",
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        self.assertEqual(len(table["data"]), 2)

    def test_tap_sync_maxrec_not_bypassed_by_line_comment(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": "SELECT catalog FROM last_update ORDER BY catalog --",
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        self.assertEqual(len(table["data"]), 2)

    def test_tap_sync_maxrec_not_bypassed_by_unterminated_block_comment(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": ("SELECT catalog FROM last_update ORDER BY catalog) AS _tap_sync LIMIT 10000 /*"),
                "maxrec": 2,
            },
        )
        self.assertEqual(response.status_code, 500)

    def test_tap_sync_rejects_semicolon_separated_queries(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": ("SELECT catalog FROM last_update LIMIT 1; SELECT catalog FROM last_update LIMIT 1"),
            },
        )
        self.assertEqual(response.status_code, 500)

    def test_tap_sync_like_with_percent_wildcard(self) -> None:
        response = self.client.get(
            "/api/v1/tap/sync",
            params={
                "query": "SELECT catalog FROM last_update WHERE catalog NOT LIKE '%icrs%'",
            },
        )
        self.assertEqual(response.status_code, 200)
        table = response.json()["data"]["resource"]["table"]
        self.assertEqual([c["name"] for c in table["columns"]], ["catalog"])
        self.assertTrue(all("icrs" not in row[0] for row in table["data"]))

    def test_tap_sync_query_timeout(self) -> None:
        with self.assertRaises(psycopg.errors.QueryCanceled):
            self.pg.query("SELECT pg_sleep(2)", timeout_seconds=1)

    def test_reader_cannot_write(self) -> None:
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.reader_storage.exec("INSERT INTO common.bib (year, author, title) VALUES (2000, ARRAY['x'], 'y')")
