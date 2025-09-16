from typing import final

import structlog
from astropy import coordinates
from astropy import units as u

from app.data import model
from app.data.repositories import layer0, layer2
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
    cz = obj.cz * u.Unit("km/s")
    e_cz = obj.e_cz * u.Unit("km/s")
    c_km_s = astronomy.to(astronomy.const("c"), "km/s")

    z = astronomy.to(cz / c_km_s)
    e_z = astronomy.to(e_cz / c_km_s)

    return adminapi.Redshift(z=z, e_z=e_z), adminapi.Velocity(
        heliocentric=adminapi.HeliocentricVelocity(
            v=astronomy.to(cz, "km/s"),
            e_v=astronomy.to(e_cz, "km/s"),
        )
    )


@final
class CrossmatchManager:
    def __init__(self, layer0_repo: layer0.Layer0Repository, layer2_repo: layer2.Layer2Repository) -> None:
        self.layer0_repo = layer0_repo
        self.layer2_repo = layer2_repo

    def get_crossmatch_records(self, r: adminapi.GetRecordsCrossmatchRequest) -> adminapi.GetRecordsCrossmatchResponse:
        table_metadata = self.layer0_repo.fetch_metadata_by_name(r.table_name)
        table_id = table_metadata.table_id
        if table_id is None:
            raise ValueError(f"Table {r.table_name} not found")

        offset = r.page * r.page_size

        status_enum = None
        if r.status != "all":  # TODO
            try:
                status_enum = enums.RecordCrossmatchStatus(r.status)
            except ValueError:
                return adminapi.GetRecordsCrossmatchResponse(records=[], units_schema=self._create_units_schema())

        processed_objects = self.layer0_repo.get_processed_objects(
            table_id=table_id,
            limit=r.page_size,
            offset=str(offset) if offset > 0 else None,
            status=status_enum,
        )

        records = []
        for obj in processed_objects:
            record = self._convert_to_crossmatch_record(obj)
            records.append(record)

        return adminapi.GetRecordsCrossmatchResponse(records=records, units_schema=self._create_units_schema())

    def _create_units_schema(self) -> adminapi.UnitsSchema:
        return adminapi.UnitsSchema(
            coordinates={
                "equatorial": {"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
                "galactic": {"lon": "deg", "lat": "deg", "e_lon": "deg", "e_lat": "deg"},
            },
            velocity={"heliocentric": {"v": "km/s", "e_v": "km/s"}},
        )

    def _convert_to_crossmatch_record(self, obj: model.Layer0ProcessedObject) -> adminapi.RecordCrossmatch:
        metadata = adminapi.RecordCrossmatchMetadata()
        if isinstance(obj.processing_result, model.CIResultObjectExisting):
            metadata.pgc = obj.processing_result.pgc
        elif isinstance(obj.processing_result, model.CIResultObjectCollision):
            metadata.possible_matches = list(obj.processing_result.pgcs) if obj.processing_result.pgcs else None

        catalogs = adminapi.Catalogs()

        if (icrs := obj.get(model.ICRSCatalogObject)) is not None:
            catalogs.coordinates = icrs_to_response(icrs)

        if (designation := obj.get(model.DesignationCatalogObject)) is not None:
            catalogs.designation = adminapi.Designation(name=designation.designation)

        if (redshift := obj.get(model.RedshiftCatalogObject)) is not None:
            catalogs.redshift, catalogs.velocity = redshift_to_response(redshift)

        status = enums.RecordCrossmatchStatus.UNPROCESSED

        for result_type, stat in status_map.items():
            if isinstance(obj.processing_result, result_type):
                status = stat

        return adminapi.RecordCrossmatch(
            record_id=obj.object_id,
            status=status,
            metadata=metadata,
            catalogs=catalogs,
        )

    def get_record_crossmatch(self, r: adminapi.GetRecordCrossmatchRequest) -> adminapi.GetRecordCrossmatchResponse:
        processed_objects = self.layer0_repo.get_processed_objects(
            limit=1,
            object_id=r.record_id,
        )

        if not processed_objects:
            raise NotFoundError(entity=r.record_id, entity_name="record")

        obj = processed_objects[0]
        crossmatch_record = self._convert_to_crossmatch_record(obj)

        candidate_pgcs: list[int] = []

        if isinstance(obj.processing_result, model.CIResultObjectCollision):
            candidate_pgcs.extend(obj.processing_result.pgcs)
        elif isinstance(obj.processing_result, model.CIResultObjectExisting):
            candidate_pgcs.append(obj.processing_result.pgc)

        if len(candidate_pgcs) == 0:
            return adminapi.GetRecordCrossmatchResponse(
                data={},
                crossmatch=crossmatch_record,
                candidates=[],
                units_schema=self._create_units_schema(),
            )

        layer2_objects = self.layer2_repo.query_pgc(
            catalogs=[model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION, model.RawCatalog.REDSHIFT],
            pgc_numbers=list(candidate_pgcs),
            limit=len(candidate_pgcs),
            offset=0,
        )

        candidates = []
        for layer2_obj in layer2_objects:
            catalogs = adminapi.Catalogs()

            if (icrs := layer2_obj.get(model.ICRSCatalogObject)) is not None:
                catalogs.coordinates = icrs_to_response(icrs)

            if (designation := layer2_obj.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = adminapi.Designation(name=designation.designation)

            if (redshift := layer2_obj.get(model.RedshiftCatalogObject)) is not None:
                catalogs.redshift, catalogs.velocity = redshift_to_response(redshift)

            candidates.append(
                adminapi.PGCCandidate(
                    pgc=layer2_obj.pgc,
                    catalogs=catalogs,
                )
            )

        return adminapi.GetRecordCrossmatchResponse(
            data={},
            crossmatch=crossmatch_record,
            candidates=candidates,
            units_schema=self._create_units_schema(),
        )
