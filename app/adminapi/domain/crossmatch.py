from collections.abc import Callable
from typing import final

import pydantic

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer0
from app.lib.crossmatch.matching import match_records, results_to_rows
from app.lib.storage import enums
from app.lib.web.errors import ConflictError, InternalError, NotFoundError, RuleValidationError
from app.specs import adminapi as spec


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
    def __init__(self, repo: repository.Repository, prefect: PrefectClient | None = None) -> None:
        self._repo = repo
        self._prefect = prefect

    def start(self, request: spec.StartCrossmatchRequest) -> spec.StartCrossmatchResponse:
        if self._prefect is None:
            raise InternalError("prefect client is not configured")
        try:
            params = spec.CrossmatchParams.model_validate(request.params)
        except pydantic.ValidationError as exc:
            raise RuleValidationError(str(exc)) from exc
        task_id = self._prefect.create_flow_run(
            name="Crossmatch/crossmatch",
            parameters={"params": params.model_dump()},
        )
        return spec.StartCrossmatchResponse(task_id=task_id)

    def preview(self, request: spec.PreviewCrossmatchRequest) -> spec.PreviewCrossmatchResponse:
        pgc_column = request.pgc_column.strip()
        if pgc_column:
            info = self._repo.get_table_metadata(layer0.RAWDATA_SCHEMA, request.table_name)
            if not info.columns:
                raise NotFoundError(entity_name="table", entity=request.table_name)
            if pgc_column not in info.columns:
                raise RuleValidationError(f"column {pgc_column} not found in {request.table_name}")
        try:
            record_ids, total = self._repo.sample_crossmatch_records(request.table_name, request.limit)
        except RuntimeError as exc:
            if "not in layer0.tables" not in str(exc):
                raise
            raise NotFoundError(entity_name="table", entity=request.table_name) from exc

        radius_deg = request.radius / 3600.0
        rows = self._repo.fetch_crossmatch_neighbors(record_ids, radius_deg)
        record_pgc_by_id = (
            self._repo.fetch_claimed_pgcs(request.table_name, pgc_column, record_ids) if pgc_column else {}
        )
        claimed = {pgc for pgc in record_pgc_by_id.values() if pgc is not None}
        existing_pgcs = self._repo.layer2_pgcs(list(claimed))
        designations = [row["new_design"] for row in rows if row["new_design"] is not None]
        matched = match_records(
            rows,
            radius_deg=radius_deg,
            pgc_column=pgc_column or None,
            redshift_tolerance=request.redshift_tolerance if request.redshift_tolerance > 0 else None,
            record_pgc_by_id=record_pgc_by_id,
            existing_pgcs=existing_pgcs,
            design_to_pgcs=self._repo.pgcs_by_designation(list(dict.fromkeys(str(item) for item in designations))),
        )
        written = {
            record_id: candidates
            for record_id, _triage, candidates in results_to_rows([(item.record_id, item.result) for item in matched])
        }
        by_id = {item.record_id: item for item in matched}
        preview_rows = [
            spec.PreviewCrossmatchRow(
                record_id=record_id,
                status=item.result.status.value,
                triage=item.result.triage_status.value,
                reason=item.result.pending_reason.value if item.result.pending_reason is not None else "",
                candidates=written.get(record_id, []),
                designation=item.designation,
                ra=item.ra,
                dec=item.dec,
                neighbors=[
                    spec.PreviewCrossmatchNeighbor(
                        pgc=neighbor.pgc,
                        distance_arcsec=round(neighbor.distance_deg * 3600, 2),
                        design=neighbor.design,
                    )
                    for neighbor in item.neighbors
                ],
            )
            for record_id in record_ids
            if (item := by_id.get(record_id)) is not None
        ]
        return spec.PreviewCrossmatchResponse(rows=preview_rows, total_count=total)

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
        if request.assignments is not None:
            pgcs = {item.record_id: item.pgc for item in request.assignments}
            requested = {pgc for pgc in pgcs.values() if pgc is not None}
            existing = self._repo.get_existing_pgcs(list(requested))
            for pgc in requested:
                if pgc not in existing:
                    raise NotFoundError(entity_name="pgc", entity=str(pgc))
            self._repo.upsert_pgc(pgcs)
            return spec.AssignRecordPgcsResponse()

        unique_ids = list(dict.fromkeys(request.record_ids or []))
        try:
            self._repo.assign_record_pgcs(unique_ids)
        except repository.AssignRecordPgcsPreconditionError as e:
            raise ConflictError(
                f"{e.count} records cannot be assigned a PGC (missing crossmatch, not resolved, or collided)",
                sample_record_ids=e.sample,
                count=e.count,
            ) from e
        return spec.AssignRecordPgcsResponse()
