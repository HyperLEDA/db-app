import pathlib
import unittest
from unittest import mock

import structlog
from starlette import testclient

import app.dataapi.command as dataapi_command
from app.data import enums as data_enums
from app.data import repositories
from app.dataapi import clients, domain
from app.dataapi.presentation.server import Server
from app.lib.storage import postgres
from app.specs import fieldapi as fieldapi_spec
from tests import lib


class _MockFieldAPIClient(clients.FieldAPIClient):
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        return [0.03, 0.12][: len(coordinates)]


class ReddeningAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
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
        cls.reader_storage = postgres.PgStorage(reader_config, cls.log, data_enums.PG_ENUM_REGISTRY)
        cls.reader_storage.connect()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.reader_storage.disconnect()

    def setUp(self) -> None:
        self.actions = domain.Actions(
            layer2_repo=repositories.Layer2Repository(self.reader_storage, self.log),
            catalog_cfg=self.cfg.catalogs,
            metadata_repo=repositories.MetadataRepository(self.reader_storage),
            references_repo=repositories.ReferencesRepository(self.reader_storage),
            fieldapi_client=_MockFieldAPIClient(),
        )
        self.client = testclient.TestClient(Server(self.actions, self.cfg.server, self.log).app)

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_calculate_reddening_landolt_batch(self) -> None:
        response = self.client.post(
            "/api/v1/calculate/reddening",
            json={
                "photsys": "Landolt",
                "coordinates": [
                    {"ra": 187.6, "dec": 15.26},
                    {"ra": 210.25, "dec": -3.1},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["photsys"], "Landolt")
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["ebv"], 0.03)
        self.assertEqual(data["results"][1]["ebv"], 0.12)
        self.assertGreater(len(data["results"][0]["filters"]), 0)
        self.assertIn("filter", data["results"][0]["filters"][0])
        self.assertIn("wavelength", data["results"][0]["filters"][0])
        self.assertIn("a", data["results"][0]["filters"][0])

    def test_calculate_reddening_unknown_photys(self) -> None:
        response = self.client.post(
            "/api/v1/calculate/reddening",
            json={
                "photsys": "UnknownSystem",
                "coordinates": [{"ra": 187.6, "dec": 15.26}],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_calculate_reddening_empty_coordinates(self) -> None:
        response = self.client.post(
            "/api/v1/calculate/reddening",
            json={
                "photsys": "Landolt",
                "coordinates": [],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_fieldapi_client_uses_fieldapi_specs(self) -> None:
        with mock.patch("app.dataapi.clients.fieldapi.requests.post") as post:
            post.return_value.raise_for_status = mock.Mock()
            post.return_value.json.return_value = {"data": {"values": [0.05]}}

            client = clients.RequestsFieldAPIClient("http://fieldapi:8082")
            values = client.sample_sfd_ebv([fieldapi_spec.SkyCoordinate(ra_deg=187.6, dec_deg=15.26)])

            self.assertEqual(values, [0.05])
            post.assert_called_once_with(
                "http://fieldapi:8082/api/v1/sample",
                json={"dataset": "sfd", "coordinates": [{"ra_deg": 187.6, "dec_deg": 15.26}]},
                timeout=10.0,
            )
