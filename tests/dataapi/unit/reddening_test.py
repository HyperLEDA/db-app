import unittest
from unittest import mock

from app.data.repositories.references import ReddeningCoefficient, ReddeningPhotometricSystem
from app.dataapi import clients, domain, responders
from app.lib.web import errors
from app.specs import dataapi as spec
from app.specs import fieldapi as fieldapi_spec


class _FakeFieldAPIClient(clients.FieldAPIClient):
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        return [0.03, 0.12][: len(coordinates)]


class _FakeReferencesRepository:
    def list_reddening(self, photsys: str, r_v: str = "3.1") -> list[ReddeningCoefficient]:
        if photsys != "Landolt":
            return []
        return [
            ReddeningCoefficient(filter="U", lambda_eff=3508.2, a_ebv=4.334),
            ReddeningCoefficient(filter="V", lambda_eff=5421.7, a_ebv=2.742),
        ]

    def list_reddening_systems(self, r_v: str = "3.1") -> list[ReddeningPhotometricSystem]:
        return [
            ReddeningPhotometricSystem(id="Landolt", description="Landolt photometric system"),
            ReddeningPhotometricSystem(id="SDSS", description="Sloan Digital Sky Survey"),
        ]


class CalculateReddeningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = domain.Actions(
            layer2_repo=mock.Mock(),
            catalog_cfg=responders.CatalogConfig.model_validate(
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
            ),
            metadata_repo=mock.Mock(),
            references_repo=_FakeReferencesRepository(),
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
        self.assertEqual(response.results[1].ebv, 0.12)
        self.assertEqual(response.results[0].filters[0].filter, "U")
        self.assertAlmostEqual(response.results[0].filters[0].a, 4.334 * 0.03)
        self.assertAlmostEqual(response.results[1].filters[1].a, 2.742 * 0.12)

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
