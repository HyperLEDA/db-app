import pytest

from app.dataapi import domain, model, repository
from app.dataapi.domain import reddening
from app.dataapi.responders.structured_responder import StructuredResponder
from app.lib.web import errors
from app.specs import dataapi as spec
from app.specs import fieldapi as fieldapi_spec


class _FakeFieldAPIClient(fieldapi_spec.FieldAPIClient):
    def __init__(self) -> None:
        self.sampled_coordinates: list[fieldapi_spec.SkyCoordinate] = []

    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        self.sampled_coordinates = coordinates
        return [0.03 + index * 0.01 for index in range(len(coordinates))]


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


@pytest.fixture
def reddening_service() -> reddening.Reddening:
    return reddening.Reddening(_FakeRepository(), _FakeFieldAPIClient())


def test_calculate_batches_unique_coordinates() -> None:
    fieldapi_client = _FakeFieldAPIClient()
    service = reddening.Reddening(_FakeRepository(), fieldapi_client)
    coord_a = spec.J2000Coordinate(ra=187.6, dec=15.26)
    coord_b = spec.J2000Coordinate(ra=210.25, dec=-3.1)

    results = service.calculate(
        [
            reddening.ReddeningQuery("Landolt", coord_a),
            reddening.ReddeningQuery("Landolt", coord_b),
            reddening.ReddeningQuery("SDSS", coord_a),
        ]
    )

    assert len(fieldapi_client.sampled_coordinates) == 2
    assert results[0].filters[0].a == pytest.approx(4.334 * 0.03)
    assert results[1].filters[0].a == pytest.approx(4.334 * 0.04)
    assert results[2].filters[0].a == pytest.approx(3.237 * 0.03)


def test_calculate_reddening_returns_results_in_input_order() -> None:
    actions = domain.Actions(repo=_FakeRepository(), fieldapi_client=_FakeFieldAPIClient())
    response = actions.calculate_reddening(
        spec.CalculateReddeningRequest(
            photsys="Landolt",
            coordinates=[
                spec.J2000Coordinate(ra=187.6, dec=15.26),
                spec.J2000Coordinate(ra=210.25, dec=-3.1),
            ],
        )
    )

    assert response.results[0].ebv == 0.03
    assert response.results[1].ebv == 0.04
    assert response.results[0].filters[0].a == pytest.approx(4.334 * 0.03)


def test_calculate_reddening_unknown_photys() -> None:
    actions = domain.Actions(repo=_FakeRepository(), fieldapi_client=_FakeFieldAPIClient())
    with pytest.raises(errors.NotFoundError):
        actions.calculate_reddening(
            spec.CalculateReddeningRequest(
                photsys="Unknown",
                coordinates=[spec.J2000Coordinate(ra=187.6, dec=15.26)],
            )
        )


def test_build_response_returns_observed_and_corrected_photometry(
    reddening_service: reddening.Reddening,
) -> None:
    responder = StructuredResponder(reddening_service)
    objects = [
        model.Layer2Object(
            pgc=5001,
            catalogs=model.Catalogs(
                objects=model.ObjectsCatalog(
                    name="NGC 4321",
                    objtype="G",
                    ra=187.6,
                    e_ra=0.0,
                    dec=15.26,
                    e_dec=0.0,
                    galactic_l=240.0,
                    galactic_b=70.0,
                    sgl=90.0,
                    sgb=10.0,
                    ebv=0.03,
                ),
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

    catalogs = responder.build_response(objects).objects[0].catalogs
    assert catalogs.designation is not None
    assert catalogs.designation.name == "NGC 4321"
    assert catalogs.nature is not None
    assert catalogs.nature.type_name == "G"
    assert catalogs.coordinates is not None
    assert catalogs.coordinates.galactic.lon == pytest.approx(240.0)
    assert catalogs.photometry_total is not None
    assert len(catalogs.photometry_total) == 2
    assert catalogs.photometry_total_corrected is not None
    assert len(catalogs.photometry_total_corrected) == 1
    assert catalogs.photometry_total_corrected[0].mag == pytest.approx(13.0 - 3.237 * 0.03)


def test_build_response_without_ebv_has_no_corrected_photometry(
    reddening_service: reddening.Reddening,
) -> None:
    responder = StructuredResponder(reddening_service)
    objects = [
        model.Layer2Object(
            pgc=5001,
            catalogs=model.Catalogs(
                objects=model.ObjectsCatalog(
                    name="NGC 4321",
                    objtype=None,
                    ra=187.6,
                    e_ra=0.0,
                    dec=15.26,
                    e_dec=0.0,
                    galactic_l=240.0,
                    galactic_b=70.0,
                    sgl=90.0,
                    sgb=10.0,
                    ebv=None,
                ),
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

    catalogs = responder.build_response(objects).objects[0].catalogs
    assert catalogs.photometry_total is not None
    assert catalogs.photometry_total_corrected is None
