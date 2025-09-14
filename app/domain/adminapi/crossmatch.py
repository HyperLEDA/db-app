from typing import final

import structlog
from astropy import constants, coordinates
from astropy import units as u

from app.data import model
from app.data.repositories import layer0
from app.lib.storage import enums
from app.presentation import adminapi

logger = structlog.stdlib.get_logger()

status_map = {
    model.CIResultObjectNew: enums.RecordCrossmatchStatus.NEW,
    model.CIResultObjectExisting: enums.RecordCrossmatchStatus.EXISTING,
    model.CIResultObjectCollision: enums.RecordCrossmatchStatus.COLLIDED,
}


@final
class CrossmatchManager:
    def __init__(self, layer0_repo: layer0.Layer0Repository) -> None:
        self.layer0_repo = layer0_repo

    def get_crossmatch_records(self, r: adminapi.GetRecordsCrossmatchRequest) -> adminapi.GetRecordsCrossmatchResponse:
        table_metadata = self.layer0_repo.fetch_metadata_by_name(r.table_name)
        table_id = table_metadata.table_id
        if table_id is None:
            raise ValueError(f"Table {r.table_name} not found")

        offset = r.page * r.page_size

        # Convert status string to enum if not "all"
        status_enum = None
        if r.status != "all":
            try:
                status_enum = enums.RecordCrossmatchStatus(r.status)
            except ValueError:
                # Invalid status, return empty results
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

        designation_obj = obj.get(model.DesignationCatalogObject)
        if designation_obj:
            catalogs.designation = adminapi.Designation(name=designation_obj.designation)

        icrs_obj = obj.get(model.ICRSCatalogObject)
        if icrs_obj:
            icrs_coords = coordinates.ICRS(ra=icrs_obj.ra * u.Unit("deg"), dec=icrs_obj.dec * u.Unit("deg"))
            galactic_coords = icrs_coords.transform_to(coordinates.Galactic())

            catalogs.coordinates = adminapi.Coordinates(
                equatorial=adminapi.EquatorialCoordinates(
                    ra=icrs_obj.ra,
                    dec=icrs_obj.dec,
                    e_ra=icrs_obj.e_ra,
                    e_dec=icrs_obj.e_dec,
                ),
                galactic=adminapi.GalacticCoordinates(
                    lon=galactic_coords.l.deg,
                    lat=galactic_coords.b.deg,
                    e_lon=icrs_obj.e_ra,
                    e_lat=icrs_obj.e_dec,
                ),
            )

        redshift_obj = obj.get(model.RedshiftCatalogObject)
        if redshift_obj:
            cz = redshift_obj.cz * u.Unit("km/s")
            e_cz = redshift_obj.e_cz * u.Unit("km/s")
            c_km_s = constants.c.to(u.Unit("km/s"))

            z = (cz / c_km_s).value
            e_z = (e_cz / c_km_s).value

            catalogs.redshift = adminapi.Redshift(z=z, e_z=e_z)

            catalogs.velocity = adminapi.Velocity(
                heliocentric=adminapi.HeliocentricVelocity(
                    v=cz.value,
                    e_v=e_cz.value,
                )
            )

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
