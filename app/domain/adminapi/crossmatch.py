from typing import final

import structlog
from astropy import coordinates
from astropy import units as u

from app.data import model
from app.data.repositories import layer0
from app.lib.storage import enums
from app.presentation import adminapi

logger = structlog.stdlib.get_logger()


@final
class CrossmatchManager:
    def __init__(self, layer0_repo: layer0.Layer0Repository) -> None:
        self.layer0_repo = layer0_repo

    def get_crossmatch_records(self, r: adminapi.GetCrossmatchRecordsRequest) -> adminapi.GetCrossmatchRecordsResponse:
        table_metadata = self.layer0_repo.fetch_metadata_by_name(r.table_name)
        table_id = table_metadata.table_id
        if table_id is None:
            raise ValueError(f"Table {r.table_name} not found")

        offset = r.page * r.page_size

        processed_objects = self.layer0_repo.get_processed_objects(
            table_id=table_id,
            limit=r.page_size,
            offset=str(offset) if offset > 0 else None,
            status=r.status,
        )

        records = []
        for obj in processed_objects:
            record = self._convert_to_crossmatch_record(obj)
            records.append(record)

        return adminapi.GetCrossmatchRecordsResponse(records=records, units_schema=self._create_units_schema())

    def _create_units_schema(self) -> adminapi.UnitsSchema:
        return adminapi.UnitsSchema(
            coordinates={
                "equatorial": {"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
                "galactic": {"lon": "deg", "lat": "deg", "e_lon": "deg", "e_lat": "deg"},
            },
            velocity={"heliocentric": {"v": "km/s", "e_v": "km/s"}},
        )

    def _get_object_status(self, obj: model.Layer0ProcessedObject) -> enums.ObjectCrossmatchStatus:
        if isinstance(obj.processing_result, model.CIResultObjectNew):
            return enums.ObjectCrossmatchStatus.NEW
        if isinstance(obj.processing_result, model.CIResultObjectExisting):
            return enums.ObjectCrossmatchStatus.EXISTING
        if isinstance(obj.processing_result, model.CIResultObjectCollision):
            return enums.ObjectCrossmatchStatus.COLLIDED
        return enums.ObjectCrossmatchStatus.UNPROCESSED

    def _convert_to_crossmatch_record(self, obj: model.Layer0ProcessedObject) -> adminapi.CrossmatchRecord:
        # Extract metadata
        metadata = adminapi.CrossmatchRecordMetadata()
        if isinstance(obj.processing_result, model.CIResultObjectExisting):
            metadata.pgc = obj.processing_result.pgc
        elif isinstance(obj.processing_result, model.CIResultObjectCollision):
            if obj.processing_result.pgcs:
                metadata.possible_matches = list(obj.processing_result.pgcs)
            elif obj.processing_result.possible_pgcs:
                # Flatten all possible PGCs from different crossmatchers
                all_pgcs = set()
                for pgc_set in obj.processing_result.possible_pgcs.values():
                    all_pgcs.update(pgc_set)
                metadata.possible_matches = list(all_pgcs)

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
            z = redshift_obj.cz / 299792458.0
            e_z = redshift_obj.e_cz / 299792458.0

            catalogs.redshift = adminapi.Redshift(z=z, e_z=e_z)

            catalogs.velocity = adminapi.Velocity(
                heliocentric=adminapi.HeliocentricVelocity(
                    v=redshift_obj.cz / 1000.0,
                    e_v=redshift_obj.e_cz / 1000.0,
                )
            )

        return adminapi.CrossmatchRecord(
            record_id=obj.object_id,
            status=self._get_object_status(obj).value,
            metadata=metadata,
            catalogs=catalogs,
        )
