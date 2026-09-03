import pytest

from app.dataapi import clients, domain, model, repository, responders
from app.dataapi.domain import reddening
from app.dataapi.responders.structured_responder import StructuredResponder
from app.lib.web import errors
from app.specs import dataapi as spec
from app.specs import fieldapi as fieldapi_spec


class _FakeFieldAPIClient(clients.FieldAPIClient):
    def __init__(self) -> None:
        self.sampled_coordinates: list[fieldapi_spec.SkyCoordinate] = []

    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        self.sampled_coordinates = coordinates
        return [0.03 + index * 0.01 for index in range(len(coordinates))]


class _FailingFieldAPIClient(clients.FieldAPIClient):
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        raise errors.InternalError("fieldapi unavailable")


class _FakeRepository:
    def list_reddening(self, photsys: str, r_v: str = "3.1") -> list[repository.ReddeningCoefficient]:
        if photsys == "Landolt":
            return [
                repository.ReddeningCoefficient(filter="U", lambda_eff=3508.2, a_ebv=4.334),
                repository.ReddeningCoefficient(filter="V", lambda_eff=5421.7, a_ebv=2.742),
            ]
        if photsys == "SDSS":
            return [
                repository.ReddeningCoefficient(filter="g", lambda_eff=4702.5, a_ebv=3.237),
            ]
        return []

    def list_reddening_systems(self, r_v: str = "3.1") -> list[repository.ReddeningPhotometricSystem]:
        return [
            repository.ReddeningPhotometricSystem(id="Landolt", description="Landolt photometric system"),
            repository.ReddeningPhotometricSystem(id="SDSS", description="Sloan Digital Sky Survey"),
        ]


def _catalog_config() -> responders.CatalogConfig:
    return responders.CatalogConfig.model_validate(
        {
            "velocity": {
                "apexes": {
                    "heliocentric": {
                        "lon": {"value": 0, "error": 0},
                        "lat": {"value": 0, "error": 0},
                        "vel": {"value": 0, "error": 0},
                    }
                }
            }
        }
    )


@pytest.fixture
def reddening_service() -> tuple[_FakeFieldAPIClient, reddening.Reddening]:
    fieldapi_client = _FakeFieldAPIClient()
    return fieldapi_client, reddening.Reddening(_FakeRepository(), fieldapi_client)


def test_calculate_batches_unique_coordinates(
    reddening_service: tuple[_FakeFieldAPIClient, reddening.Reddening],
) -> None:
    fieldapi_client, reddening_instance = reddening_service
    coord_a = spec.J2000Coordinate(ra=187.6, dec=15.26)
    coord_b = spec.J2000Coordinate(ra=210.25, dec=-3.1)
    queries = [
        reddening.ReddeningQuery("Landolt", coord_a),
        reddening.ReddeningQuery("Landolt", coord_b),
        reddening.ReddeningQuery("SDSS", coord_a),
    ]

    results = reddening_instance.calculate(queries)

    assert len(fieldapi_client.sampled_coordinates) == 2
    assert len(results) == 3
    assert results[0].filters[0].a == pytest.approx(4.334 * 0.03)
    assert results[1].filters[0].a == pytest.approx(4.334 * 0.04)
    assert results[2].filters[0].a == pytest.approx(3.237 * 0.03)


def test_calculate_returns_empty_filters_for_unknown_photsys(
    reddening_service: tuple[_FakeFieldAPIClient, reddening.Reddening],
) -> None:
    _, reddening_instance = reddening_service
    results = reddening_instance.calculate([reddening.ReddeningQuery("Unknown", spec.J2000Coordinate(ra=1.0, dec=2.0))])

    assert results[0].filters == []


def test_list_references(reddening_service: tuple[_FakeFieldAPIClient, reddening.Reddening]) -> None:
    _, reddening_instance = reddening_service
    response = reddening_instance.list_references()

    assert len(response.systems) == 2
    assert response.systems[0].id == "Landolt"


@pytest.fixture
def actions() -> domain.Actions:
    return domain.Actions(
        repo=_FakeRepository(),
        catalog_cfg=_catalog_config(),
        fieldapi_client=_FakeFieldAPIClient(),
    )


def test_calculate_reddening_returns_results_in_input_order(actions: domain.Actions) -> None:
    response = actions.calculate_reddening(
        spec.CalculateReddeningRequest(
            photsys="Landolt",
            coordinates=[
                spec.J2000Coordinate(ra=187.6, dec=15.26),
                spec.J2000Coordinate(ra=210.25, dec=-3.1),
            ],
        )
    )

    assert response.photsys == "Landolt"
    assert len(response.results) == 2
    assert response.results[0].ebv == 0.03
    assert response.results[1].ebv == 0.04
    assert response.results[0].filters[0].filter == "U"
    assert response.results[0].filters[0].a == pytest.approx(4.334 * 0.03)
    assert response.results[1].filters[1].a == pytest.approx(2.742 * 0.04)


def test_calculate_reddening_unknown_photys(actions: domain.Actions) -> None:
    with pytest.raises(errors.NotFoundError):
        actions.calculate_reddening(
            spec.CalculateReddeningRequest(
                photsys="Unknown",
                coordinates=[spec.J2000Coordinate(ra=187.6, dec=15.26)],
            )
        )


def test_list_reddening_references_returns_systems(actions: domain.Actions) -> None:
    response = actions.list_reddening_references()

    assert len(response.systems) == 2
    assert response.systems[0].id == "Landolt"
    assert response.systems[0].description == "Landolt photometric system"
    assert response.systems[1].id == "SDSS"


@pytest.fixture
def structured_responder() -> tuple[_FakeFieldAPIClient, StructuredResponder]:
    fieldapi_client = _FakeFieldAPIClient()
    reddening_instance = reddening.Reddening(_FakeRepository(), fieldapi_client)
    return fieldapi_client, StructuredResponder(_catalog_config(), reddening_instance)


def test_build_response_returns_observed_and_corrected_photometry(
    structured_responder: tuple[_FakeFieldAPIClient, StructuredResponder],
) -> None:
    fieldapi_client, responder = structured_responder
    icrs = model.ICRSCatalog(ra=187.6, e_ra=0.0, dec=15.26, e_dec=0.0)
    objects = [
        model.Layer2Object(
            pgc=5001,
            catalogs=model.Catalogs(
                icrs=icrs,
                photometry_total=model.PhotometryTotalCatalog(
                    measurements=[
                        model.PhotometryTotalMeasurement(
                            band="V",
                            magsys="Vega",
                            method="psf",
                            wavelength=5501.4,
                            mag=12.5,
                            e_mag=0.1,
                            photsys="UBVRIJHKL",
                            filter="V",
                        ),
                        model.PhotometryTotalMeasurement(
                            band="g",
                            magsys="AB",
                            method="psf",
                            wavelength=4702.5,
                            mag=13.0,
                            e_mag=0.1,
                            photsys="SDSS",
                            filter="g",
                        ),
                    ]
                ),
            ),
        )
    ]

    response = responder.build_response(objects)

    assert len(fieldapi_client.sampled_coordinates) == 1
    catalogs = response.objects[0].catalogs
    assert catalogs.photometry_total is not None
    assert len(catalogs.photometry_total) == 2
    assert catalogs.photometry_total[0].mag == pytest.approx(12.5)
    assert catalogs.photometry_total[1].mag == pytest.approx(13.0)
    assert catalogs.photometry_total_corrected is not None
    assert len(catalogs.photometry_total_corrected) == 1
    corrected = catalogs.photometry_total_corrected[0]
    assert corrected.band == "g"
    assert corrected.mag == pytest.approx(13.0 - 3.237 * 0.03)


def test_build_response_degrades_when_fieldapi_unavailable() -> None:
    reddening_instance = reddening.Reddening(_FakeRepository(), _FailingFieldAPIClient())
    responder = StructuredResponder(_catalog_config(), reddening_instance)
    icrs = model.ICRSCatalog(ra=187.6, e_ra=0.0, dec=15.26, e_dec=0.0)
    objects = [
        model.Layer2Object(
            pgc=5001,
            catalogs=model.Catalogs(
                icrs=icrs,
                photometry_total=model.PhotometryTotalCatalog(
                    measurements=[
                        model.PhotometryTotalMeasurement(
                            band="g",
                            magsys="AB",
                            method="psf",
                            wavelength=4702.5,
                            mag=13.0,
                            e_mag=0.1,
                            photsys="SDSS",
                            filter="g",
                        ),
                    ]
                ),
            ),
        )
    ]

    response = responder.build_response(objects)

    catalogs = response.objects[0].catalogs
    assert catalogs.photometry_total is not None
    assert len(catalogs.photometry_total) == 1
    assert catalogs.photometry_total[0].mag == pytest.approx(13.0)
    assert catalogs.photometry_total_corrected is None


def test_build_response_without_icrs_has_no_corrected_photometry(
    structured_responder: tuple[_FakeFieldAPIClient, StructuredResponder],
) -> None:
    fieldapi_client, responder = structured_responder
    objects = [
        model.Layer2Object(
            pgc=5001,
            catalogs=model.Catalogs(
                photometry_total=model.PhotometryTotalCatalog(
                    measurements=[
                        model.PhotometryTotalMeasurement(
                            band="g",
                            magsys="AB",
                            method="psf",
                            wavelength=4702.5,
                            mag=13.0,
                            e_mag=0.1,
                            photsys="SDSS",
                            filter="g",
                        ),
                    ]
                ),
            ),
        )
    ]

    response = responder.build_response(objects)

    assert fieldapi_client.sampled_coordinates == []
    catalogs = response.objects[0].catalogs
    assert catalogs.photometry_total is not None
    assert catalogs.photometry_total_corrected is None
