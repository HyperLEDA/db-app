from dataclasses import dataclass
from typing import final

from app.data import repositories
from app.data.repositories.references import ReddeningCoefficient
from app.dataapi import clients
from app.specs import dataapi as spec
from app.specs import fieldapi as fieldapi_spec


@dataclass(frozen=True)
class ReddeningQuery:
    photsys: str
    coordinate: spec.J2000Coordinate


@final
class Reddening:
    def __init__(
        self,
        references_repo: repositories.ReferencesRepository,
        fieldapi_client: clients.FieldAPIClient,
        r_v: str = "3.1",
    ) -> None:
        self._references_repo = references_repo
        self._fieldapi_client = fieldapi_client
        self._r_v = r_v

    def calculate(self, queries: list[ReddeningQuery]) -> list[spec.ReddeningAtPosition]:
        if not queries:
            return []

        coord_key_to_index: dict[tuple[float, float], int] = {}
        unique_coords: list[fieldapi_spec.SkyCoordinate] = []
        query_coord_indices: list[int] = []
        for query in queries:
            key = (query.coordinate.ra, query.coordinate.dec)
            if key not in coord_key_to_index:
                coord_key_to_index[key] = len(unique_coords)
                unique_coords.append(
                    fieldapi_spec.SkyCoordinate(ra_deg=query.coordinate.ra, dec_deg=query.coordinate.dec)
                )
            query_coord_indices.append(coord_key_to_index[key])

        ebv_values = self._fieldapi_client.sample_sfd_ebv(unique_coords)

        photsys_coefficients: dict[str, list[ReddeningCoefficient]] = {}
        for query in queries:
            if query.photsys not in photsys_coefficients:
                photsys_coefficients[query.photsys] = self._references_repo.list_reddening(query.photsys, self._r_v)

        results: list[spec.ReddeningAtPosition] = []
        for query, coord_index in zip(queries, query_coord_indices, strict=True):
            ebv = ebv_values[coord_index]
            coefficients = photsys_coefficients[query.photsys]
            results.append(
                spec.ReddeningAtPosition(
                    ebv=ebv,
                    filters=[
                        spec.ReddeningFilterValue(
                            filter=coefficient.filter,
                            wavelength=coefficient.lambda_eff,
                            a=coefficient.a_ebv * ebv,
                        )
                        for coefficient in coefficients
                    ],
                )
            )
        return results

    def list_references(self) -> spec.ListReddeningReferencesResponse:
        systems = self._references_repo.list_reddening_systems(self._r_v)
        return spec.ListReddeningReferencesResponse(
            systems=[
                spec.ReddeningPhotometricSystem(id=system.id, description=system.description) for system in systems
            ]
        )
