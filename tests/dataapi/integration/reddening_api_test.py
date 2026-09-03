import pathlib
from collections.abc import Generator
from unittest import mock

import pytest
import structlog
from starlette import testclient

import app.dataapi.command as dataapi_command
from app.dataapi import clients, domain, repository
from app.dataapi.presentation.server import Server
from app.lib.storage import enums, postgres
from app.specs import fieldapi as fieldapi_spec
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


class _MockFieldAPIClient(clients.FieldAPIClient):
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        return [0.03, 0.12][: len(coordinates)]


@pytest.fixture(scope="module")
def dataapi_config() -> dataapi_command.Config:
    cfg_path = pathlib.Path(__file__).resolve().parents[3] / "configs" / "dev" / "dataapi.yaml"
    return dataapi_command.parse_config(str(cfg_path))


@pytest.fixture(scope="module")
def log() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()


@pytest.fixture(scope="module")
def reader_storage(pg_storage: PostgresTestStorage, log: structlog.stdlib.BoundLogger) -> Generator[postgres.PgStorage]:
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
        fieldapi_client=_MockFieldAPIClient(),
    )
    return testclient.TestClient(Server(actions, dataapi_config.server, log).app)


def test_calculate_reddening_landolt_batch(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/calculator/reddening",
        json={
            "photsys": "Landolt",
            "coordinates": [
                {"ra": 187.6, "dec": 15.26},
                {"ra": 210.25, "dec": -3.1},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["photsys"] == "Landolt"
    assert len(data["results"]) == 2
    assert data["results"][0]["ebv"] == 0.03
    assert data["results"][1]["ebv"] == 0.12
    assert len(data["results"][0]["filters"]) > 0
    assert "filter" in data["results"][0]["filters"][0]
    assert "wavelength" in data["results"][0]["filters"][0]
    assert "a" in data["results"][0]["filters"][0]


def test_calculate_reddening_unknown_photys(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/calculator/reddening",
        json={
            "photsys": "UnknownSystem",
            "coordinates": [{"ra": 187.6, "dec": 15.26}],
        },
    )
    assert response.status_code == 404


def test_calculate_reddening_empty_coordinates(client: testclient.TestClient) -> None:
    response = client.post(
        "/api/v1/calculator/reddening",
        json={
            "photsys": "Landolt",
            "coordinates": [],
        },
    )
    assert response.status_code == 400


def test_list_reddening_references(client: testclient.TestClient) -> None:
    response = client.get("/api/v1/references/reddening")
    assert response.status_code == 200
    systems = response.json()["data"]["systems"]
    assert len(systems) > 0
    system_ids = {system["id"] for system in systems}
    assert "Landolt" in system_ids
    assert "SDSS" in system_ids
    for system in systems:
        assert "id" in system
        assert "description" in system
        assert system["description"]

    reddening_response = client.post(
        "/api/v1/calculator/reddening",
        json={
            "photsys": systems[0]["id"],
            "coordinates": [{"ra": 187.6, "dec": 15.26}],
        },
    )
    assert reddening_response.status_code == 200


def test_fieldapi_client_uses_fieldapi_specs() -> None:
    response = mock.MagicMock()
    response.json.return_value = {"data": {"values": [0.05]}}
    with mock.patch("requests.post", return_value=response) as post:
        client = clients.RequestsFieldAPIClient("http://fieldapi:8082")
        values = client.sample_sfd_ebv([fieldapi_spec.SkyCoordinate(ra_deg=187.6, dec_deg=15.26)])

        assert values == [0.05]
        post.assert_called_once_with(
            "http://fieldapi:8082/api/v1/sample",
            json={"dataset": "sfd", "coordinates": [{"ra_deg": 187.6, "dec_deg": 15.26}]},
            timeout=10.0,
        )
