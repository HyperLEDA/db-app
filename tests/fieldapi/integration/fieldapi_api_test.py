import pytest
import structlog
from starlette import testclient

from app.fieldapi import domain
from app.fieldapi.presentation import server
from app.fieldapi.providers import registry
from app.lib import auth
from app.lib.web import server as web_server
from app.specs import fieldapi


class _MockProvider:
    def sample(self, coordinates: list[fieldapi.SkyCoordinate]) -> list[float]:
        _ = coordinates
        return [0.03, 0.12]


@pytest.fixture
def client() -> testclient.TestClient:
    log = structlog.get_logger()
    dataset_registry = registry.DatasetRegistry(
        providers={"sfd": _MockProvider()},
        metadata={
            "sfd": fieldapi.DatasetInfo(
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
    actions = domain.Actions(dataset_registry)
    server_config = web_server.ServerConfig(host="127.0.0.1", port=8082)
    return testclient.TestClient(
        server.Server(actions, server_config, log, auth.NoopAuthenticator(), auth_enabled=False).app
    )


def test_list_datasets(client: testclient.TestClient) -> None:
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    datasets = response.json()["data"]["datasets"]
    assert len(datasets) == 1
    assert datasets[0]["id"] == "sfd"
    assert datasets[0]["quantity"] == "ebv"


def test_sample_returns_values_in_order(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/sample",
        json={
            "dataset": "sfd",
            "coordinates": [
                {"ra_deg": 187.6, "dec_deg": 15.26},
                {"ra_deg": 210.25, "dec_deg": -3.10},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["values"] == [0.03, 0.12]


def test_sample_unknown_dataset(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/sample",
        json={
            "dataset": "missing",
            "coordinates": [{"ra_deg": 187.6, "dec_deg": 15.26}],
        },
    )
    assert response.status_code == 404


def test_sample_validation_error(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/sample",
        json={"dataset": "sfd", "coordinates": []},
    )
    assert response.status_code == 400
