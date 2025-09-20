from typing import final

import structlog
from astropy import coordinates
from astropy import units as u

from app.data import model
from app.data.repositories import layer0, layer1, layer2
from app.lib import astronomy
from app.lib.storage import enums
from app.lib.web.errors import NotFoundError
from app.presentation import adminapi

logger = structlog.stdlib.get_logger()

status_map = {
    model.CIResultObjectNew: enums.RecordCrossmatchStatus.NEW,
    model.CIResultObjectExisting: enums.RecordCrossmatchStatus.EXISTING,
    model.CIResultObjectCollision: enums.RecordCrossmatchStatus.COLLIDED,
}

DATA_SCHEMA = adminapi.Schema(
    units=adminapi.UnitsSchema(
        coordinates={
            "equatorial": {"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
            "galactic": {"lon": "deg", "lat": "deg", "e_lon": "deg", "e_lat": "deg"},
        },
        velocity={"heliocentric": {"v": "km/s", "e_v": "km/s"}},
    )
)


def icrs_to_response(obj: model.ICRSCatalogObject) -> adminapi.Coordinates:
    icrs_coords = coordinates.ICRS(ra=obj.ra * u.Unit("deg"), dec=obj.dec * u.Unit("deg"))
    galactic_coords = icrs_coords.transform_to(coordinates.Galactic())

    return adminapi.Coordinates(
        equatorial=adminapi.EquatorialCoordinates(
            ra=obj.ra,
            dec=obj.dec,
            e_ra=obj.e_ra,
            e_dec=obj.e_dec,
        ),
        galactic=adminapi.GalacticCoordinates(
            lon=galactic_coords.l.deg,
            lat=galactic_coords.b.deg,
            e_lon=obj.e_ra,
            e_lat=obj.e_dec,
        ),
    )


def redshift_to_response(obj: model.RedshiftCatalogObject) -> tuple[adminapi.Redshift, adminapi.Velocity]:
    cz = obj.cz * u.Unit("m/s")
    e_cz = obj.e_cz * u.Unit("m/s")

    z = astronomy.to(cz / astronomy.const("c"))
    e_z = astronomy.to(e_cz / astronomy.const("c"))

    return adminapi.Redshift(z=z, e_z=e_z), adminapi.Velocity(
        heliocentric=adminapi.HeliocentricVelocity(
            v=astronomy.to(cz, "km/s"),
            e_v=astronomy.to(e_cz, "km/s"),
        )
    )


@final
class CrossmatchManager:
    def __init__(
        self,
        layer0_repo: layer0.Layer0Repository,
        layer1_repo: layer1.Layer1Repository,
        layer2_repo: layer2.Layer2Repository,
    ) -> None:
        self.layer0_repo = layer0_repo
        self.layer1_repo = layer1_repo
        self.layer2_repo = layer2_repo

    def get_crossmatch_records(self, r: adminapi.GetRecordsCrossmatchRequest) -> adminapi.GetRecordsCrossmatchResponse:
        offset = r.page * r.page_size

        processed_objects = self.layer0_repo.get_processed_records(
            table_name=r.table_name,
            limit=r.page_size,
            offset=str(offset) if offset > 0 else None,
            status=r.status,
        )

        records = self._convert_to_record_crossmatch(processed_objects)

        return adminapi.GetRecordsCrossmatchResponse(records=records, schema=DATA_SCHEMA)

    def _convert_to_record_crossmatch(self, records: list[model.RecordCrossmatch]) -> list[adminapi.RecordCrossmatch]:
        record_ids = [obj.record.id for obj in records]
        layer1_data = self.layer1_repo.query_records(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION, model.RawCatalog.REDSHIFT],
            record_ids=record_ids,
        )
        layer1_data_map = {rec.id: rec for rec in layer1_data}

        result = []
        for obj in records:
            metadata = adminapi.RecordCrossmatchMetadata()
            if isinstance(obj.processing_result, model.CIResultObjectExisting):
                metadata.pgc = obj.processing_result.pgc
            elif isinstance(obj.processing_result, model.CIResultObjectCollision):
                metadata.possible_matches = list(obj.processing_result.pgcs) if obj.processing_result.pgcs else None

            catalogs = adminapi.Catalogs()

            record = layer1_data_map.get(obj.record.id)
            if record is None:
                raise RuntimeError(f"expected 1 record for id {obj.record.id}, got none")

            if (icrs := record.get(model.ICRSCatalogObject)) is not None:
                catalogs.coordinates = icrs_to_response(icrs)

            if (designation := record.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = adminapi.Designation(name=designation.designation)

            if (redshift := record.get(model.RedshiftCatalogObject)) is not None:
                catalogs.redshift, catalogs.velocity = redshift_to_response(redshift)

            status = enums.RecordCrossmatchStatus.UNPROCESSED

            if (t := type(obj.processing_result)) in status_map:
                status = status_map[t]

            result.append(
                adminapi.RecordCrossmatch(
                    record_id=obj.record.id,
                    status=status,
                    metadata=metadata,
                    catalogs=catalogs,
                )
            )

        return result

    def get_record_crossmatch(self, r: adminapi.GetRecordCrossmatchRequest) -> adminapi.GetRecordCrossmatchResponse:
        processed_objects = self.layer0_repo.get_processed_records(
            limit=1,
            record_id=r.record_id,
        )

        if not processed_objects:
            raise NotFoundError(entity=r.record_id, entity_name="record")

        obj = processed_objects[0]
        crossmatch_records = self._convert_to_record_crossmatch([obj])

        candidate_pgcs: list[int] = []

        if isinstance(obj.processing_result, model.CIResultObjectCollision):
            candidate_pgcs.extend(obj.processing_result.pgcs)
        elif isinstance(obj.processing_result, model.CIResultObjectExisting):
            candidate_pgcs.append(obj.processing_result.pgc)

        response = adminapi.GetRecordCrossmatchResponse(
            crossmatch=crossmatch_records[0],
            candidates=[],
            schema=DATA_SCHEMA,
        )

        if len(candidate_pgcs) == 0:
            return response

        layer2_objects = self.layer2_repo.query_pgc(
            catalogs=[model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION, model.RawCatalog.REDSHIFT],
            pgc_numbers=list(candidate_pgcs),
            limit=len(candidate_pgcs),
            offset=0,
        )

        for layer2_obj in layer2_objects:
            catalogs = adminapi.Catalogs()

            if (icrs := layer2_obj.get(model.ICRSCatalogObject)) is not None:
                catalogs.coordinates = icrs_to_response(icrs)

            if (designation := layer2_obj.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = adminapi.Designation(name=designation.designation)

            if (redshift := layer2_obj.get(model.RedshiftCatalogObject)) is not None:
                catalogs.redshift, catalogs.velocity = redshift_to_response(redshift)

            response.candidates.append(
                adminapi.PGCCandidate(
                    pgc=layer2_obj.pgc,
                    catalogs=catalogs,
                )
            )

        return response
