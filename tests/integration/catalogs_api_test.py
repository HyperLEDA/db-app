import unittest

import structlog
from starlette import testclient

from app.data import repositories
from app.domain import adminapi as domain
from app.domain.adminapi.mock import get_mock_table_stats_cache
from app.lib import audit, auth, clients
from app.lib.web import server
from app.presentation.adminapi.server import Server
from tests import lib


class CatalogsAPITest(unittest.TestCase):
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

    def _catalogs_by_name(self) -> dict[str, dict]:
        response = self.client.get("/admin/api/v1/catalogs")
        self.assertEqual(response.status_code, 200)
        return {c["catalog"]: c for c in response.json()["data"]["catalogs"]}

    def test_get_catalogs_icrs(self) -> None:
        catalogs = self._catalogs_by_name()
        icrs = catalogs["icrs"]
        fields = {f["name"]: f for f in icrs["fields"]}
        self.assertEqual(set(fields), {"ra", "dec", "e_ra", "e_dec"})
        for name in ("ra", "dec", "e_ra", "e_dec"):
            self.assertTrue(fields[name]["required"])
            self.assertEqual(fields[name]["data_type"], "float")
        self.assertEqual(fields["ra"]["unit"], "deg")
        self.assertEqual(fields["dec"]["unit"], "deg")
        self.assertEqual(fields["e_ra"]["unit"], "deg")
        self.assertEqual(fields["e_dec"]["unit"], "deg")

    def test_get_catalogs_geometry(self) -> None:
        catalogs = self._catalogs_by_name()
        geometry = catalogs["geometry"]
        fields = {f["name"]: f for f in geometry["fields"]}
        self.assertEqual(
            set(fields),
            {"band", "method", "level", "a", "e_a", "b", "e_b", "pa", "e_pa", "isophote", "e_isophote"},
        )
        self.assertTrue(fields["band"]["required"])
        self.assertTrue(fields["method"]["required"])
        self.assertFalse(fields["level"]["required"])
        self.assertFalse(fields["pa"]["required"])
        self.assertEqual(fields["a"]["unit"], "arcsec")
        self.assertEqual(fields["isophote"]["unit"], "mag/arcmin2")
        self.assertEqual(fields["method"]["data_type"], "str")

    def test_runtime_catalogs_excluded(self) -> None:
        catalogs = self._catalogs_by_name()
        self.assertNotIn("additional_designations", catalogs)
