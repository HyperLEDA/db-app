import pathlib
import unittest

import structlog
from starlette import testclient

from app.commands.adminapi import command as adminapi_command
from app.commands.dataapi import command as dataapi_command
from app.data import repositories
from app.domain import adminapi as admin_domain
from app.domain import dataapi as dataapi_domain
from app.domain.adminapi import mock as admin_mock
from app.domain.designation import DesignationFormatter, RuleEngine
from app.lib import audit, auth, clients
from app.presentation.adminapi.server import Server as AdminServer
from app.presentation.dataapi.server import Server as DataAPIServer
from tests import lib

GOLDEN_CASES: list[tuple[str, str, str]] = [
    ("pgc 1234", "PGC 1234", "pgc"),
    ("LEDA 001", "PGC 1", "pgc"),
    ("ngc 0224", "NGC 224", "ngc"),
    ("NGC 1234A", "NGC 1234A", "ngc"),
    ("ic 0342", "IC 342", "ic"),
    ("messier 31", "M 31", "m"),
    ("2mass j12345678+1234567", "2MASS J12345678+1234567", "2mass"),
    ("3C 84", "3C 084", "3c"),
    ("ACO S123", "ACO S 123", "abell"),
    ("ACO 123", "ACO 123", "abell-13"),
    ("And III", "And 3", "andromeda"),
    ("MCG 1-2-3", "MCG +01-02-003", "mcg"),
    ("totally unknown xyz", "totally unknown xyz", ""),
]

IDEMPOTENT_CASES = [
    ("pgc 1234", "PGC 1234"),
    ("ngc 0224", "NGC 224"),
    ("messier 31", "M 31"),
]

TEST_RULE_IDS = ("test", "bad", "disableme")


def _formatter_from_repo(pg: repositories.DesignationRulesRepository) -> DesignationFormatter:
    return DesignationFormatter(pg.snapshot)


class DesignationFormatIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.log = structlog.get_logger()
        cfg_path = pathlib.Path(__file__).resolve().parents[2] / "configs" / "dev" / "dataapi.yaml"
        cls.cfg = dataapi_command.parse_config(str(cfg_path))

    def setUp(self) -> None:
        self.pg = self.pg_storage.get_storage()
        self.rules_repo = repositories.DesignationRulesRepository(self.pg, self.log)
        self.engine = RuleEngine.compile([r.to_engine_rule() for r in self.rules_repo.snapshot().rules])
        self.data_client = testclient.TestClient(
            DataAPIServer(
                dataapi_domain.Actions(
                    layer2_repo=repositories.Layer2Repository(self.pg, self.log),
                    catalog_cfg=self.cfg.catalogs,
                    metadata_repo=repositories.MetadataRepository(self.pg),
                    designation_formatter=_formatter_from_repo(self.rules_repo),
                ),
                self.cfg.server,
                self.log,
                auth.NoopAuthenticator(),
            ).app
        )

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_format_batch(self) -> None:
        response = self.data_client.post(
            "/api/v1/designation/format",
            json={"names": ["ngc 224", "unknown name xyz"]},
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["data"]["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["formatted"], "NGC 224")
        self.assertEqual(results[0]["rule_id"], "ngc")
        self.assertIsNone(results[1]["rule_id"])
        self.assertEqual(results[1]["formatted"], "unknown name xyz")

    def test_golden_cases(self) -> None:
        for raw, expected, rule_id in GOLDEN_CASES:
            with self.subTest(raw=raw):
                result = self.engine.format(raw)
                if rule_id:
                    self.assertIsNotNone(result)
                    assert result is not None
                    self.assertEqual(result.formatted, expected)
                    self.assertEqual(result.rule_id, rule_id)
                else:
                    self.assertIsNone(result)

    def test_idempotency(self) -> None:
        for raw, expected in IDEMPOTENT_CASES:
            with self.subTest(raw=raw):
                first = self.engine.format(raw)
                assert first is not None
                second = self.engine.format(first.formatted)
                self.assertIsNotNone(second)
                assert second is not None
                self.assertEqual(second.formatted, expected)


class DesignationRulesIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.log = structlog.get_logger()
        cfg_path = pathlib.Path(__file__).resolve().parents[2] / "configs" / "dev" / "adminapi.yaml"
        cls.cfg = adminapi_command.parse_config(str(cfg_path))
        pg = cls.pg_storage.get_storage()
        cls.migration_rule_count = len(repositories.DesignationRulesRepository(pg, cls.log).list_rules())

    def setUp(self) -> None:
        self.pg = self.pg_storage.get_storage()
        self.rules_repo = repositories.DesignationRulesRepository(self.pg, self.log)
        self.client = testclient.TestClient(
            AdminServer(
                admin_domain.Actions(
                    common_repo=repositories.CommonRepository(self.pg, self.log),
                    layer0_repo=repositories.Layer0Repository(self.pg, self.log),
                    layer1_repo=repositories.Layer1Repository(self.pg, self.log),
                    layer2_repo=repositories.Layer2Repository(self.pg, self.log),
                    designation_rules_repo=self.rules_repo,
                    authenticator=auth.NoopAuthenticator(),
                    clients=clients.Clients(ads_token="test"),
                    table_stats_cache=admin_mock.get_mock_table_stats_cache(),
                ),
                self.cfg.server,
                self.log,
                auth.NoopAuthenticator(),
                action_recorder=audit.NoopActionRecorder(),
                auth_enabled=False,
            ).app
        )

    def tearDown(self) -> None:
        for rule_id in TEST_RULE_IDS:
            self.pg.exec("DELETE FROM designation.format_rules WHERE id = %s", params=[rule_id])
        self.pg_storage.clear()

    def test_list_rules_after_migration(self) -> None:
        response = self.client.get("/admin/api/v1/designation/rules")
        self.assertEqual(response.status_code, 200)
        rules = response.json()["data"]["rules"]
        self.assertEqual(len(rules), self.migration_rule_count)
        self.assertGreater(self.migration_rule_count, 0)

    def test_save_new_rule(self) -> None:
        response = self.client.post(
            "/admin/api/v1/designation/rule",
            json={
                "rule": {
                    "id": "test",
                    "priority": 9999,
                    "pattern": r"^TEST\s*(\d+)$",
                    "template": "TEST {0}",
                    "transforms": {},
                    "enabled": True,
                },
                "examples": [{"input": "TEST 42", "expected": "TEST 42"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        rule = response.json()["data"]["rule"]
        self.assertEqual(rule["id"], "test")

    def test_save_rejects_bad_example(self) -> None:
        response = self.client.post(
            "/admin/api/v1/designation/rule",
            json={
                "rule": {
                    "id": "bad",
                    "priority": 9998,
                    "pattern": r"^BAD\s*(\d+)$",
                    "template": "BAD {0}",
                    "transforms": {},
                    "enabled": True,
                },
                "examples": [{"input": "BAD 1", "expected": "WRONG"}],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_disable_rule(self) -> None:
        create = self.client.post(
            "/admin/api/v1/designation/rule",
            json={
                "rule": {
                    "id": "disableme",
                    "priority": 9997,
                    "pattern": r"^DISABLEME\s*(\d+)$",
                    "template": "DISABLEME {0}",
                    "transforms": {},
                    "enabled": True,
                },
                "examples": [{"input": "DISABLEME 1", "expected": "DISABLEME 1"}],
            },
        )
        self.assertEqual(create.status_code, 200)
        rule = create.json()["data"]["rule"]

        disable = self.client.post(
            "/admin/api/v1/designation/rule",
            json={
                "rule": {**rule, "enabled": False},
            },
        )
        self.assertEqual(disable.status_code, 200)
        disabled = disable.json()["data"]["rule"]
        self.assertFalse(disabled["enabled"])

        snapshot = self.rules_repo.snapshot()
        self.assertTrue(all(r.id != rule["id"] for r in snapshot.rules))

    def test_rules_repo_snapshot(self) -> None:
        snapshot = self.rules_repo.snapshot()
        self.assertEqual(len(snapshot.rules), self.migration_rule_count)
        self.assertGreater(snapshot.version, 0)
