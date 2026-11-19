import random
from collections import Counter
from collections.abc import Callable
from typing import final

import pydantic

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer0
from app.lib.crossmatch.matching import (
    DistributionKey,
    distribution_key,
    distribution_rows,
    match_records,
    results_to_rows,
)
from app.lib.crossmatch.models import MatchedRecord, TriageStatus
from app.lib.crossmatch.parameters import parameters_payload
from app.lib.storage import enums, sql_row_filter
from app.lib.web.errors import ConflictError, InternalError, NotFoundError, RuleValidationError
from app.specs import adminapi as spec

_PREVIEW_SAMPLE_SIZE = 1000
_PREVIEW_RETURN_SIZE = 10


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


def _preview_row(item: MatchedRecord, candidates: list[int]) -> spec.PreviewCrossmatchRow:
    return spec.PreviewCrossmatchRow(
        record_id=item.record_id,
        status=item.result.status.value,
        triage=item.result.triage_status.value,
        parameters=spec.PreviewCrossmatchParameters.model_validate(parameters_payload(item.result.parameters)),
        candidates=candidates,
        designation=item.designation,
        ra=item.ra,
        dec=item.dec,
        neighbors=[
            spec.PreviewCrossmatchNeighbor(
                pgc=neighbor.pgc,
                ra=neighbor.ra,
                dec=neighbor.dec,
                distance_arcsec=round(neighbor.distance_deg * 3600, 2),
                design=neighbor.design,
            )
            for neighbor in item.neighbors
        ],
    )


def _sample_by_triage(
    matched: list[MatchedRecord],
    triage: TriageStatus,
    limit: int,
) -> list[MatchedRecord]:
    pool = [item for item in matched if item.result.triage_status == triage]
    if len(pool) > limit:
        return random.sample(pool, limit)
    return pool


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
        include_pgc = request.include_pgc
        include_redshift = request.include_redshift
        pgc_column = request.pgc_column.strip() if include_pgc else ""
        if include_pgc:
            if not pgc_column:
                raise RuleValidationError("pgc_column is required when include_pgc is true")
            info = self._repo.get_table_metadata(layer0.RAWDATA_SCHEMA, request.table_name)
            if not info.columns:
                raise NotFoundError(entity_name="table", entity=request.table_name)
            if pgc_column not in info.columns:
                raise RuleValidationError(f"column {pgc_column} not found in {request.table_name}")
        if include_redshift and not (request.redshift_tolerance > 0):
            raise RuleValidationError("redshift_tolerance must be greater than 0 when include_redshift is true")
        row_filter = sql_row_filter.row_filter_clause(request.row_filter)
        try:
            record_ids, eligible, total = self._repo.sample_crossmatch_records(
                request.table_name,
                _PREVIEW_SAMPLE_SIZE,
                row_filter,
            )
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
            redshift_tolerance=request.redshift_tolerance if include_redshift else None,
            record_pgc_by_id=record_pgc_by_id,
            existing_pgcs=existing_pgcs,
            design_to_pgcs=self._repo.pgcs_by_designation(list(dict.fromkeys(str(item) for item in designations))),
            include_pgc=include_pgc,
            include_redshift=include_redshift,
            include_nature=request.include_nature,
        )
        written = {
            record_id: candidates
            for record_id, _triage, candidates in results_to_rows([(item.record_id, item.result) for item in matched])
        }
        counts: Counter[DistributionKey] = Counter()
        for item in matched:
            counts[distribution_key(item.result)] += 1
        sample_count = len(matched)
        pending_rows = [
            _preview_row(item, written.get(item.record_id, []))
            for item in _sample_by_triage(matched, TriageStatus.PENDING, _PREVIEW_RETURN_SIZE)
        ]
        resolved_rows = [
            _preview_row(item, written.get(item.record_id, []))
            for item in _sample_by_triage(matched, TriageStatus.RESOLVED, _PREVIEW_RETURN_SIZE)
        ]
        statistics = [spec.PreviewCrossmatchStat.model_validate(row) for row in distribution_rows(counts, sample_count)]
        return spec.PreviewCrossmatchResponse(
            pending_rows=pending_rows,
            resolved_rows=resolved_rows,
            total_count=total,
            eligible_count=eligible,
            sample_count=sample_count,
            statistics=statistics,
        )

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
