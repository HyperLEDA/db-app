from typing import Any, final

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

    def set_crossmatch_results(self, r: adminapi.SetCrossmatchResultsRequest) -> adminapi.SetCrossmatchResultsResponse:
        rows: list[tuple[str, enums.RecordTriageStatus, list[int]]] = []
        payload = r.statuses

        if payload.new is not None:
            default_triage = enums.RecordTriageStatus.RESOLVED
            for i, record_id in enumerate(payload.new.record_ids):
                triage_override = payload.new.triage_statuses[i] if i < len(payload.new.triage_statuses) else None
                triage = triage_override if triage_override is not None else default_triage
                rows.append((record_id, triage, []))

        if payload.existing is not None:
            default_triage = enums.RecordTriageStatus.RESOLVED
            for i, record_id in enumerate(payload.existing.record_ids):
                triage_override = (
                    payload.existing.triage_statuses[i] if i < len(payload.existing.triage_statuses) else None
                )
                triage = triage_override if triage_override is not None else default_triage
                rows.append((record_id, triage, [payload.existing.pgcs[i]]))

        if payload.collided is not None:
            default_triage = enums.RecordTriageStatus.PENDING
            for i, record_id in enumerate(payload.collided.record_ids):
                triage_override = (
                    payload.collided.triage_statuses[i] if i < len(payload.collided.triage_statuses) else None
                )
                triage = triage_override if triage_override is not None else default_triage
                rows.append((record_id, triage, list(payload.collided.possible_matches[i])))

        if rows:
            self.layer0_repo.set_crossmatch_results(rows)
        return adminapi.SetCrossmatchResultsResponse()

    def get_crossmatch_records(self, r: adminapi.GetRecordsCrossmatchRequest) -> adminapi.GetRecordsCrossmatchResponse:
        row_offset = r.page * r.page_size

        processed_rows = self.layer0_repo.get_processed_records(
            table_name=r.table_name,
            limit=r.page_size,
            row_offset=row_offset if row_offset > 0 else None,
            status=[r.status] if r.status is not None else None,
            triage_status=[r.triage_status] if r.triage_status is not None else None,
        )

        records = self._convert_to_record_crossmatch(processed_rows)

        return adminapi.GetRecordsCrossmatchResponse(records=records, schema=DATA_SCHEMA)

    def _candidates_to_status(self, candidates: list[int]) -> enums.RecordCrossmatchStatus:
        if len(candidates) == 0:
            return enums.RecordCrossmatchStatus.NEW
        if len(candidates) == 1:
            return enums.RecordCrossmatchStatus.EXISTING
        return enums.RecordCrossmatchStatus.COLLIDED

    def _convert_to_record_crossmatch(self, rows: list[model.CrossmatchRecordRow]) -> list[adminapi.RecordCrossmatch]:
        record_ids = [row.record_id for row in rows]
        layer1_data = self.layer1_repo.query_records(
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION, model.RawCatalog.REDSHIFT],
            record_ids=record_ids,
        )
        layer1_data_map = {rec.id: rec for rec in layer1_data}

        result = []
        for row in rows:
            metadata = adminapi.RecordCrossmatchMetadata()
            if len(row.candidates) == 1:
                metadata.pgc = row.candidates[0]
            elif len(row.candidates) > 1:
                metadata.possible_matches = row.candidates

            catalogs = adminapi.Catalogs()

            record = layer1_data_map.get(row.record_id)
            if record is None:
                raise RuntimeError(f"expected 1 record for id {row.record_id}, got none")

            if (icrs := record.get(model.ICRSCatalogObject)) is not None:
                catalogs.coordinates = icrs_to_response(icrs)

            if (designation := record.get(model.DesignationCatalogObject)) is not None:
                catalogs.designation = adminapi.Designation(name=designation.designation)

            if (redshift := record.get(model.RedshiftCatalogObject)) is not None:
                catalogs.redshift, catalogs.velocity = redshift_to_response(redshift)

            status = self._candidates_to_status(row.candidates)

            result.append(
                adminapi.RecordCrossmatch(
                    record_id=row.record_id,
                    status=status,
                    triage_status=row.triage_status,
                    metadata=metadata,
                    catalogs=catalogs,
                )
            )

        return result

    def get_record_crossmatch(self, r: adminapi.GetRecordCrossmatchRequest) -> adminapi.GetRecordCrossmatchResponse:
        processed_rows = self.layer0_repo.get_processed_records(
            limit=1,
            record_id=r.record_id,
        )

        if not processed_rows:
            raise NotFoundError(entity=r.record_id, entity_name="record")

        row = processed_rows[0]
        crossmatch_records = self._convert_to_record_crossmatch([row])

        original_data: dict[str, Any] | None = None
        table_name = ""
        try:
            raw_data = self.layer0_repo.fetch_raw_data(record_id=row.record_id)
            table_name = raw_data.table_name
            if not raw_data.data.empty:
                original_data = raw_data.data.iloc[0].to_dict()
        except Exception:
            logger.warning(
                "Failed to fetch original raw data for record",
                record_id=row.record_id,
                error=True,
            )

        candidate_pgcs = list(row.candidates)

        response = adminapi.GetRecordCrossmatchResponse(
            table_name=table_name,
            crossmatch=crossmatch_records[0],
            candidates=[],
            schema=DATA_SCHEMA,
            original_data=original_data,
        )

        if len(candidate_pgcs) == 0:
            return response

        layer2_objects = self.layer2_repo.query_catalogs_pgc(
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
