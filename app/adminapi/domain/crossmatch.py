from collections.abc import Callable
from typing import Any, Protocol, final

import structlog
from astropy import units as u

from app import catalogs
from app.adminapi import model, repository
from app.lib import astronomy
from app.lib.storage import enums
from app.lib.web.errors import ConflictError, NotFoundError
from app.specs import adminapi as spec

logger = structlog.stdlib.get_logger()


def _candidates_to_status(candidates: list[int]) -> enums.RecordCrossmatchStatus:
    if len(candidates) == 0:
        return enums.RecordCrossmatchStatus.NEW
    if len(candidates) == 1:
        return enums.RecordCrossmatchStatus.EXISTING
    return enums.RecordCrossmatchStatus.COLLIDED


DATA_SCHEMA = spec.Schema(
    units=spec.UnitsSchema(
        coordinates={
            "equatorial": {"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
            "galactic": {"lon": "deg", "lat": "deg", "e_lon": "arcsec", "e_lat": "arcsec"},
        },
        velocity={"heliocentric": {"v": "km/s", "e_v": "km/s"}},
    )
)


class _CatalogBearing(Protocol):
    def get[T](self, t: type[T]) -> T | None: ...


def icrs_to_response(obj: catalogs.ICRSCatalogObject) -> spec.Coordinates:
    lon, lat, e_lon, e_lat = astronomy.equatorial_to_lonlat(obj.ra, obj.dec, obj.e_ra, obj.e_dec, "galactic")

    return spec.Coordinates(
        equatorial=spec.EquatorialCoordinates(
            ra=obj.ra,
            dec=obj.dec,
            e_ra=obj.e_ra,
            e_dec=obj.e_dec,
        ),
        galactic=spec.GalacticCoordinates(
            lon=lon,
            lat=lat,
            e_lon=e_lon,
            e_lat=e_lat,
        ),
    )


def redshift_to_response(obj: catalogs.RedshiftCatalogObject) -> tuple[spec.Redshift, spec.Velocity]:
    z = astronomy.heliocentric_cz_to_z(obj.cz * u.Unit("km/s"))
    e_z = astronomy.heliocentric_cz_to_z(obj.e_cz * u.Unit("km/s"))

    return spec.Redshift(z=z, e_z=e_z), spec.Velocity(
        heliocentric=spec.HeliocentricVelocity(
            v=obj.cz,
            e_v=obj.e_cz,
        )
    )


def catalogs_from_object(obj: _CatalogBearing) -> spec.Catalogs:
    result = spec.Catalogs()

    if (icrs := obj.get(catalogs.ICRSCatalogObject)) is not None:
        result.coordinates = icrs_to_response(icrs)

    if (designation := obj.get(catalogs.DesignationCatalogObject)) is not None:
        result.designation = spec.Designation(name=designation.designation)

    if (redshift := obj.get(catalogs.RedshiftCatalogObject)) is not None:
        result.redshift, result.velocity = redshift_to_response(redshift)

    if (nature := obj.get(catalogs.NatureCatalogObject)) is not None:
        result.nature = spec.Nature(type_name=nature.type_name)

    return result


def _append_crossmatch_rows(
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
    record_ids: list[str],
    triage_statuses: list[enums.RecordTriageStatus | None],
    default_triage: enums.RecordTriageStatus,
    candidates_for_index: Callable[[int], list[int]],
) -> None:
    for i, record_id in enumerate(record_ids):
        triage_override = triage_statuses[i] if i < len(triage_statuses) else None
        triage = triage_override if triage_override is not None else default_triage
        rows.append((record_id, triage, candidates_for_index(i)))


@final
class CrossmatchManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def set_crossmatch_results(self, r: spec.SetCrossmatchResultsRequest) -> spec.SetCrossmatchResultsResponse:
        rows: list[tuple[str, enums.RecordTriageStatus, list[int]]] = []
        payload = r.statuses

        if payload.new is not None:
            _append_crossmatch_rows(
                rows,
                payload.new.record_ids,
                payload.new.triage_statuses,
                enums.RecordTriageStatus.RESOLVED,
                lambda _: [],
            )

        if payload.existing is not None:
            existing = payload.existing
            _append_crossmatch_rows(
                rows,
                existing.record_ids,
                existing.triage_statuses,
                enums.RecordTriageStatus.RESOLVED,
                lambda i: [existing.pgcs[i]],
            )

        if payload.collided is not None:
            collided = payload.collided
            _append_crossmatch_rows(
                rows,
                collided.record_ids,
                collided.triage_statuses,
                enums.RecordTriageStatus.PENDING,
                lambda i: list(collided.possible_matches[i]),
            )

        if rows:
            self._repo.set_crossmatch_results(rows)
        return spec.SetCrossmatchResultsResponse()

    def assign_record_pgcs(self, request: spec.AssignRecordPgcsRequest) -> spec.AssignRecordPgcsResponse:
        unique_ids = list(dict.fromkeys(request.record_ids))
        try:
            self._repo.assign_record_pgcs(unique_ids)
        except repository.AssignRecordPgcsPreconditionError as e:
            raise ConflictError(
                f"{e.count} records cannot be assigned a PGC (missing crossmatch, not resolved, or collided)",
                sample_record_ids=e.sample,
                count=e.count,
            ) from e
        return spec.AssignRecordPgcsResponse()

    def _convert_to_record_crossmatch(self, rows: list[model.CrossmatchRecordRow]) -> list[spec.RecordCrossmatch]:
        record_ids = [row.record_id for row in rows]
        layer1_data = self._repo.query_records(
            [
                catalogs.RawCatalog.ICRS,
                catalogs.RawCatalog.DESIGNATION,
                catalogs.RawCatalog.REDSHIFT,
                catalogs.RawCatalog.NATURE,
            ],
            record_ids=record_ids,
        )
        layer1_data_map = {rec.id: rec for rec in layer1_data}

        result = []
        for row in rows:
            metadata = spec.RecordCrossmatchMetadata()
            if len(row.candidates) == 1:
                metadata.pgc = row.candidates[0]
            elif len(row.candidates) > 1:
                metadata.possible_matches = row.candidates

            record = layer1_data_map.get(row.record_id)
            if record is None:
                raise RuntimeError(f"expected 1 record for id {row.record_id}, got none")

            status = _candidates_to_status(row.candidates)

            result.append(
                spec.RecordCrossmatch(
                    record_id=row.record_id,
                    status=status,
                    triage_status=row.triage_status,
                    metadata=metadata,
                    catalogs=catalogs_from_object(record),
                )
            )

        return result

    def get_record_crossmatch(self, r: spec.GetRecordCrossmatchRequest) -> spec.GetRecordCrossmatchResponse:
        processed_rows = self._repo.get_processed_records(
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
            raw_data = self._repo.fetch_raw_data(record_id=row.record_id)
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

        response = spec.GetRecordCrossmatchResponse(
            table_name=table_name,
            crossmatch=crossmatch_records[0],
            candidates=[],
            schema=DATA_SCHEMA,
            original_data=original_data,
        )

        if len(candidate_pgcs) == 0:
            return response

        layer2_objects = self._repo.query_catalogs_pgc(
            raw_catalogs=[
                catalogs.RawCatalog.ICRS,
                catalogs.RawCatalog.DESIGNATION,
                catalogs.RawCatalog.REDSHIFT,
                catalogs.RawCatalog.NATURE,
            ],
            pgc_numbers=list(candidate_pgcs),
            limit=len(candidate_pgcs),
            offset=0,
        )

        for layer2_obj in layer2_objects:
            response.candidates.append(
                spec.PGCCandidate(
                    pgc=layer2_obj.pgc,
                    catalogs=catalogs_from_object(layer2_obj),
                )
            )

        return response
