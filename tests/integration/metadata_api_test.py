import pathlib
import unittest

import structlog
import yaml
from starlette import testclient

from app.commands.dataapi import command as dataapi_command
from app.data import repositories
from app.domain import dataapi as domain
from app.domain.dataapi import actions as dataapi_actions
from app.lib import auth
from app.presentation.dataapi.server import Server
from tests import lib


class MetadataAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cfg_path = pathlib.Path(__file__).resolve().parents[2] / "configs" / "dev" / "dataapi.yaml"
        cls.cfg = dataapi_command.Config(**yaml.safe_load(cfg_path.read_text()))
        cls.log = structlog.get_logger()

    def setUp(self) -> None:
        self.pg = self.pg_storage.get_storage()
        self.actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.pg, self.log),
            catalog_cfg=self.cfg.catalogs,
            metadata_repo=repositories.MetadataRepository(self.pg),
        )
        self.client = testclient.TestClient(
            Server(self.actions, self.cfg.server, self.log, auth.NoopAuthenticator()).app
        )

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_list_schemas(self) -> None:
        response = self.client.get("/api/v1/schema")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("data", body)
        self.assertIn("schemas", body["data"])
        schemas = body["data"]["schemas"]
        self.assertIsInstance(schemas, list)
        self.assertGreater(len(schemas), 0)
        common = next(s for s in schemas if s["schema_name"] == "common")
        self.assertIn("tables", common)
        table_names = {t["table_name"] for t in common["tables"]}
        self.assertIn("bib", table_names)

    def test_get_table_common_bib(self) -> None:
        response = self.client.get(
            "/api/v1/table",
            params={"schema_name": "common", "table_name": "bib"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["schema_name"], "common")
        self.assertEqual(data["table_name"], "bib")
        self.assertIn("columns", data)
        col_names = {c["column_name"] for c in data["columns"]}
        self.assertIn("id", col_names)
        self.assertIn("code", col_names)
        self.assertIn("sample_rows", data)
        self.assertIsInstance(data["sample_rows"], list)
        self.assertLessEqual(len(data["sample_rows"]), 50)

    def test_get_table_not_found(self) -> None:
        response = self.client.get(
            "/api/v1/table",
            params={"schema_name": "common", "table_name": "no_such_table_zzzzz"},
        )
        self.assertEqual(response.status_code, 404)

    def test_metadata_allowed_schema_filter(self) -> None:
        response = self.client.get("/api/v1/schema")
        self.assertEqual(response.status_code, 200)
        for entry in response.json()["data"]["schemas"]:
            self.assertIn(entry["schema_name"], dataapi_actions.METADATA_ALLOWED_SCHEMAS)

    def test_get_table_rejects_schema_outside_whitelist(self) -> None:
        response = self.client.get(
            "/api/v1/table",
            params={"schema_name": "pg_catalog", "table_name": "pg_class"},
        )
        self.assertEqual(response.status_code, 404)
