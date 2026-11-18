from collections.abc import Callable
from typing import final

import pydantic

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
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
