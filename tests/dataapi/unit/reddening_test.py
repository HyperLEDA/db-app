import unittest

from app.data.model import layer2
from app.dataapi import clients, domain, repository, responders
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


class ReddeningDomainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fieldapi_client = _FakeFieldAPIClient()
        self.repo = _FakeRepository()
        self.reddening = reddening.Reddening(self.repo, self.fieldapi_client)

    def test_calculate_batches_unique_coordinates(self) -> None:
        coord_a = spec.J2000Coordinate(ra=187.6, dec=15.26)
        coord_b = spec.J2000Coordinate(ra=210.25, dec=-3.1)
        queries = [
            reddening.ReddeningQuery("Landolt", coord_a),
            reddening.ReddeningQuery("Landolt", coord_b),
            reddening.ReddeningQuery("SDSS", coord_a),
        ]

        results = self.reddening.calculate(queries)

        self.assertEqual(len(self.fieldapi_client.sampled_coordinates), 2)
        self.assertEqual(len(results), 3)
        self.assertAlmostEqual(results[0].filters[0].a, 4.334 * 0.03)
        self.assertAlmostEqual(results[1].filters[0].a, 4.334 * 0.04)
        self.assertAlmostEqual(results[2].filters[0].a, 3.237 * 0.03)

    def test_calculate_returns_empty_filters_for_unknown_photsys(self) -> None:
        results = self.reddening.calculate([reddening.ReddeningQuery("Unknown", spec.J2000Coordinate(ra=1.0, dec=2.0))])

        self.assertEqual(results[0].filters, [])

    def test_list_references(self) -> None:
        response = self.reddening.list_references()

        self.assertEqual(len(response.systems), 2)
        self.assertEqual(response.systems[0].id, "Landolt")


class CalculateReddeningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = domain.Actions(
            repo=_FakeRepository(),
            catalog_cfg=_catalog_config(),
            fieldapi_client=_FakeFieldAPIClient(),
        )

    def test_calculate_reddening_returns_results_in_input_order(self) -> None:
        response = self.actions.calculate_reddening(
            spec.CalculateReddeningRequest(
                photsys="Landolt",
                coordinates=[
                    spec.J2000Coordinate(ra=187.6, dec=15.26),
                    spec.J2000Coordinate(ra=210.25, dec=-3.1),
                ],
            )
        )

        self.assertEqual(response.photsys, "Landolt")
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.results[0].ebv, 0.03)
        self.assertEqual(response.results[1].ebv, 0.04)
        self.assertEqual(response.results[0].filters[0].filter, "U")
        self.assertAlmostEqual(response.results[0].filters[0].a, 4.334 * 0.03)
        self.assertAlmostEqual(response.results[1].filters[1].a, 2.742 * 0.04)

    def test_calculate_reddening_unknown_photys(self) -> None:
        with self.assertRaises(errors.NotFoundError):
            self.actions.calculate_reddening(
                spec.CalculateReddeningRequest(
                    photsys="Unknown",
                    coordinates=[spec.J2000Coordinate(ra=187.6, dec=15.26)],
                )
            )

    def test_list_reddening_references_returns_systems(self) -> None:
        response = self.actions.list_reddening_references()

        self.assertEqual(len(response.systems), 2)
        self.assertEqual(response.systems[0].id, "Landolt")
        self.assertEqual(response.systems[0].description, "Landolt photometric system")
        self.assertEqual(response.systems[1].id, "SDSS")


class StructuredResponderPhotometryCorrectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fieldapi_client = _FakeFieldAPIClient()
        self.reddening_service = reddening.Reddening(_FakeRepository(), self.fieldapi_client)
        self.responder = StructuredResponder(_catalog_config(), self.reddening_service)

    def test_build_response_returns_observed_and_corrected_photometry(self) -> None:
        icrs = layer2.ICRSCatalog(ra=187.6, e_ra=0.0, dec=15.26, e_dec=0.0)
        objects = [
            layer2.Layer2Object(
                pgc=5001,
                catalogs=layer2.Catalogs(
                    icrs=icrs,
                    photometry_total=layer2.PhotometryTotalCatalog(
                        measurements=[
                            layer2.PhotometryTotalMeasurement(
                                band="V",
                                magsys="Vega",
                                method="psf",
                                wavelength=5501.4,
                                mag=12.5,
                                e_mag=0.1,
                                photsys="UBVRIJHKL",
                                filter="V",
                            ),
                            layer2.PhotometryTotalMeasurement(
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

        response = self.responder.build_response(objects)

        self.assertEqual(len(self.fieldapi_client.sampled_coordinates), 1)
        catalogs = response.objects[0].catalogs
        self.assertIsNotNone(catalogs.photometry_total)
        assert catalogs.photometry_total is not None
        self.assertEqual(len(catalogs.photometry_total), 2)
        self.assertAlmostEqual(catalogs.photometry_total[0].mag, 12.5)
        self.assertAlmostEqual(catalogs.photometry_total[1].mag, 13.0)
        self.assertIsNotNone(catalogs.photometry_total_corrected)
        assert catalogs.photometry_total_corrected is not None
        self.assertEqual(len(catalogs.photometry_total_corrected), 1)
        corrected = catalogs.photometry_total_corrected[0]
        self.assertEqual(corrected.band, "g")
        self.assertAlmostEqual(corrected.mag, 13.0 - 3.237 * 0.03)

    def test_build_response_without_icrs_has_no_corrected_photometry(self) -> None:
        objects = [
            layer2.Layer2Object(
                pgc=5001,
                catalogs=layer2.Catalogs(
                    photometry_total=layer2.PhotometryTotalCatalog(
                        measurements=[
                            layer2.PhotometryTotalMeasurement(
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

        response = self.responder.build_response(objects)

        self.assertEqual(self.fieldapi_client.sampled_coordinates, [])
        catalogs = response.objects[0].catalogs
        self.assertIsNotNone(catalogs.photometry_total)
        self.assertIsNone(catalogs.photometry_total_corrected)
