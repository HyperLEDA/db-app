import unittest

import structlog
from starlette import testclient

from app.fieldapi import domain
from app.fieldapi.presentation import interface, server
from app.fieldapi.providers import registry
from app.lib import auth
from app.lib.web import server as web_server


class FieldAPIIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.log = structlog.get_logger()
        self.dataset_registry = registry.DatasetRegistry(
            providers={"sfd": _MockProvider()},
            metadata={
                "sfd": interface.DatasetInfo(
                    id="sfd",
                    name="SFD",
                    version="1998",
                    dimensions=2,
                    quantity="ebv",
                    unit="mag",
                    description="Galactic dust reddening map",
                    bibcode="1998ApJ...500..525S",
                )
            },
        )
        self.actions = domain.Actions(self.dataset_registry)
        server_config = web_server.ServerConfig(host="127.0.0.1", port=8082)
        self.client = testclient.TestClient(
            server.Server(self.actions, server_config, self.log, auth.NoopAuthenticator(), auth_enabled=False).app
        )

    def test_list_datasets(self) -> None:
        response = self.client.get("/api/v1/datasets")
        self.assertEqual(response.status_code, 200)
        datasets = response.json()["data"]["datasets"]
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]["id"], "sfd")
        self.assertEqual(datasets[0]["quantity"], "ebv")

    def test_sample_returns_values_in_order(self) -> None:
        response = self.client.post(
            "/api/v1/sample",
            json={
                "dataset": "sfd",
                "coordinates": [
                    {"ra_deg": 187.6, "dec_deg": 15.26},
                    {"ra_deg": 210.25, "dec_deg": -3.10},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["values"], [0.03, 0.12])

    def test_sample_unknown_dataset(self) -> None:
        response = self.client.post(
            "/api/v1/sample",
            json={
                "dataset": "missing",
                "coordinates": [{"ra_deg": 187.6, "dec_deg": 15.26}],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_sample_validation_error(self) -> None:
        response = self.client.post(
            "/api/v1/sample",
            json={"dataset": "sfd", "coordinates": []},
        )
        self.assertEqual(response.status_code, 400)


class _MockProvider:
    def sample(self, coordinates: list[interface.SkyCoordinate]) -> list[float]:
        _ = coordinates
        return [0.03, 0.12]
