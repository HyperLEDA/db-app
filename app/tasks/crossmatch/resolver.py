from app.tasks.crossmatch import icrs, name, object_type, pgc, redshift
from app.tasks.crossmatch.models import CrossmatchResult, CrossmatchStatus, PendingReason, RecordEvidence, TriageStatus
from app.tasks.crossmatch.preliminary import PreliminaryExisting, PreliminaryNew, PreliminaryStatus


def _pending(result: PreliminaryStatus, reason: PendingReason) -> CrossmatchResult:
    if isinstance(result, PreliminaryNew):
        return CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.PENDING, pending_reason=reason)
    if isinstance(result, PreliminaryExisting):
        return CrossmatchResult(
            status=CrossmatchStatus.EXISTING,
            triage_status=TriageStatus.PENDING,
            matched_pgc=result.pgc,
            pending_reason=reason,
        )
    return CrossmatchResult(
        status=CrossmatchStatus.COLLIDING,
        triage_status=TriageStatus.PENDING,
        colliding_pgcs=list(result.pgcs),
        pending_reason=reason,
    )


class Resolver:
    def __init__(
        self,
        radius_deg: float,
        pgc_column: str | None = None,
        redshift_tolerance: float | None = None,
    ) -> None:
        self._radius_deg = radius_deg
        self._pgc_column = pgc_column
        self._redshift_tolerance = redshift_tolerance

    @property
    def search_radius_deg(self) -> float:
        return self._radius_deg

    @property
    def pgc_column(self) -> str | None:
        return self._pgc_column

    def resolve(self, evidence: RecordEvidence) -> CrossmatchResult:
        icrs_result, pending_reason = icrs.resolve(evidence, self._radius_deg)
        if pending_reason is not None:
            return _pending(icrs_result, pending_reason)

        pgc_result, pending_reason = pgc.resolve(evidence, icrs_result)
        if pending_reason is not None:
            return _pending(pgc_result, pending_reason)

        name_result, pending_reason = name.resolve(evidence, pgc_result)
        if pending_reason is not None:
            return _pending(name_result, pending_reason)

        redshift_result, pending_reason = redshift.resolve(evidence, name_result, self._redshift_tolerance)
        if pending_reason is not None:
            return _pending(redshift_result, pending_reason)

        type_result, pending_reason = object_type.resolve(evidence, redshift_result)
        if pending_reason is not None:
            return _pending(type_result, pending_reason)

        if isinstance(type_result, PreliminaryNew):
            return CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED)
        if isinstance(type_result, PreliminaryExisting):
            return CrossmatchResult(
                status=CrossmatchStatus.EXISTING,
                triage_status=TriageStatus.RESOLVED,
                matched_pgc=type_result.pgc,
            )
        return CrossmatchResult(
            status=CrossmatchStatus.COLLIDING,
            triage_status=TriageStatus.PENDING,
            colliding_pgcs=list(type_result.pgcs),
            pending_reason=PendingReason.MULTIPLE_OBJECTS_MATCHED,
        )
