import random
from collections import defaultdict
from collections.abc import Callable
from typing import final

import pydantic

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer0
from app.lib.crossmatch import submit as crossmatch_submit
from app.lib.crossmatch.matching import (
    candidate_pgcs,
    distribution_key,
    ordered_distribution_keys,
    resolve_inputs,
    results_to_rows,
)
from app.lib.crossmatch.models import MatchedRecord
from app.lib.crossmatch.parameters import parameters_payload
from app.lib.crossmatch.resolver import Resolver
from app.lib.storage import enums, sql_row_filter
from app.lib.web.errors import ConflictError, InternalError, NotFoundError, RuleValidationError
from app.specs import adminapi as spec

_PREVIEW_RETURN_SIZE = 10
_PREVIEW_SUBMIT_ROW_LIMIT = 20


def _append_crossmatch_rows(
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
    record_ids: list[str],
    triage_statuses: list[enums.RecordTriageStatus | None],
    default_triage: enums.RecordTriageStatus,
    candidates_for_index: Callable[[int], list[int]],
) -> None:
    for i, record_id in enumerate(record_ids):
        override = triage_statuses[i] if i < len(triage_statuses) else None
        rows.append((record_id, override if override is not None else default_triage, candidates_for_index(i)))


def _preview_row(item: MatchedRecord, candidates: list[int]) -> spec.PreviewCrossmatchRow:
    return spec.PreviewCrossmatchRow(
        record_id=item.record_id,
        parameters=spec.PreviewCrossmatchParameters.model_validate(parameters_payload(item.result.parameters)),
        candidates=candidates,
        designation=item.designation,
        ra=item.ra,
        dec=item.dec,
        neighbors=[
            spec.PreviewCrossmatchNeighbor(
                pgc=n.pgc, ra=n.ra, dec=n.dec, distance_arcsec=round(n.distance_deg * 3600, 2), design=n.design
            )
            for n in item.neighbors
        ],
    )


def _statistics(matched: list[MatchedRecord], written: dict[str, list[int]]) -> list[spec.PreviewCrossmatchStat]:
    grouped: dict[tuple, list[MatchedRecord]] = defaultdict(list)
    for item in matched:
        grouped[distribution_key(item.result)].append(item)
    counts = {key: len(items) for key, items in grouped.items()}
    total = len(matched)
    return [
        spec.PreviewCrossmatchStat(
            status=status.value,
            triage=triage.value,
            parameters=spec.PreviewCrossmatchParameters.model_validate(parameters_payload(dict(parameter_items))),
            count=len(items),
            percent=round((100.0 * len(items) / total) if total else 0.0, 1),
            rows=[
                _preview_row(item, written.get(item.record_id, []))
                for item in (random.sample(items, _PREVIEW_RETURN_SIZE) if len(items) > _PREVIEW_RETURN_SIZE else items)
            ],
        )
        for status, triage, parameter_items in ordered_distribution_keys(counts)
        if (items := grouped[(status, triage, parameter_items)])
    ]


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
        return spec.StartCrossmatchResponse(
            task_id=self._prefect.create_flow_run(
                name="Crossmatch/crossmatch", parameters={"params": params.model_dump()}
            )
        )

    def start_submit(self, request: spec.StartSubmitCrossmatchRequest) -> spec.StartSubmitCrossmatchResponse:
        if self._prefect is None:
            raise InternalError("prefect client is not configured")
        try:
            params = spec.SubmitCrossmatchParams.model_validate(request.params)
        except pydantic.ValidationError as exc:
            raise RuleValidationError(str(exc)) from exc
        return spec.StartSubmitCrossmatchResponse(
            task_id=self._prefect.create_flow_run(
                name="Submit crossmatch/submit-crossmatch",
                parameters={"params": params.model_dump()},
            )
        )

    def preview_submit(self, request: spec.PreviewSubmitCrossmatchRequest) -> spec.PreviewSubmitCrossmatchResponse:
        selection = crossmatch_submit.selection_from(
            table_name=request.table_name,
            include_new=request.include_new,
            include_existing=request.include_existing,
            require_parameters=request.require_parameters,
            row_filter=request.row_filter,
        )
        try:
            eligible_percent = self._repo.estimate_submit_eligible_percent(selection)
            rows = self._repo.preview_submit_crossmatch(selection, request.sample_size)
        except RuntimeError as exc:
            if "not in layer0.tables" not in str(exc):
                raise
            raise NotFoundError(entity_name="table", entity=request.table_name) from exc
        return spec.PreviewSubmitCrossmatchResponse(
            sample_count=len(rows),
            new_count=sum(row["outcome"] == "new" for row in rows),
            existing_count=sum(row["outcome"] == "existing" for row in rows),
            eligible_percent=eligible_percent,
            rows=[spec.PreviewSubmitCrossmatchRow.model_validate(row) for row in rows[:_PREVIEW_SUBMIT_ROW_LIMIT]],
        )

    def preview(self, request: spec.PreviewCrossmatchRequest) -> spec.PreviewCrossmatchResponse:
        include_redshift = request.include_redshift
        pgc_column = request.pgc_column.strip()
        include_pgc = bool(pgc_column)
        if include_pgc:
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
                request.table_name, request.sample_size, row_filter
            )
        except RuntimeError as exc:
            if "not in layer0.tables" not in str(exc):
                raise
            raise NotFoundError(entity_name="table", entity=request.table_name) from exc

        resolver = Resolver(
            radius_deg=request.radius_arcsec / 3600.0,
            pgc_column=pgc_column or None,
            redshift_tolerance=request.redshift_tolerance if include_redshift else None,
            include_pgc=include_pgc,
            include_redshift=include_redshift,
            include_nature=request.include_nature,
        )
        inputs = self._repo.fetch_crossmatch_inputs(
            request.table_name,
            record_ids,
            resolver.pgc_column,
            resolver.search_radius_deg,
            include_redshift=include_redshift,
            include_nature=request.include_nature,
        )
        matched = resolve_inputs(inputs, resolver, self._repo.layer2_pgcs)
        written = {
            record_id: candidate_pgcs(candidates)
            for record_id, _, candidates in results_to_rows([(item.record_id, item.result) for item in matched])
        }
        return spec.PreviewCrossmatchResponse(
            total_count=total,
            eligible_count=eligible,
            sample_count=len(matched),
            statistics=_statistics(matched, written),
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
        try:
            self._repo.assign_record_pgcs(list(dict.fromkeys(request.record_ids or [])))
        except repository.AssignRecordPgcsPreconditionError as e:
            raise ConflictError(
                f"{e.count} records cannot be assigned a PGC (missing crossmatch, not resolved, or collided)",
                sample_record_ids=e.sample,
                count=e.count,
            ) from e
        return spec.AssignRecordPgcsResponse()
