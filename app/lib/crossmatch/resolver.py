from app.lib.crossmatch import icrs, name, object_type, pgc, redshift
from app.lib.crossmatch.models import CrossmatchReason, CrossmatchResult, CrossmatchStatus, RecordEvidence, TriageStatus
from app.lib.crossmatch.preliminary import PreliminaryColliding, PreliminaryExisting, PreliminaryNew, PreliminaryStatus


def _pending(result: PreliminaryStatus, reason: CrossmatchReason) -> CrossmatchResult:
    if isinstance(result, PreliminaryNew):
        return CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.PENDING, reason=reason)
    if isinstance(result, PreliminaryExisting):
        return CrossmatchResult(
            status=CrossmatchStatus.EXISTING,
            triage_status=TriageStatus.PENDING,
            matched_pgc=result.pgc,
            reason=reason,
        )
    return CrossmatchResult(
        status=CrossmatchStatus.COLLIDING,
        triage_status=TriageStatus.PENDING,
        colliding_pgcs=list(result.pgcs),
        reason=reason,
    )


def _narrowed_to_existing(
    previous: PreliminaryStatus,
    current: PreliminaryStatus,
    reason: CrossmatchReason,
    match_reason: CrossmatchReason | None,
) -> CrossmatchReason | None:
    if match_reason is not None:
        return match_reason
    if isinstance(previous, PreliminaryColliding) and isinstance(current, PreliminaryExisting):
        return reason
    return None


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
        match_reason: CrossmatchReason | None = None

        icrs_result, reason = icrs.resolve(evidence, self._radius_deg)
        if reason is not None:
            return _pending(icrs_result, reason)
        if isinstance(icrs_result, PreliminaryExisting):
            match_reason = CrossmatchReason.MATCHED_COORDINATES

        pgc_result, reason = pgc.resolve(evidence, icrs_result)
        if reason is not None:
            return _pending(pgc_result, reason)
        match_reason = _narrowed_to_existing(icrs_result, pgc_result, CrossmatchReason.MATCHED_PGC, match_reason)

        name_result, reason = name.resolve(evidence, pgc_result)
        if reason is not None:
            return _pending(name_result, reason)
        match_reason = _narrowed_to_existing(pgc_result, name_result, CrossmatchReason.MATCHED_NAME, match_reason)

        redshift_result, reason = redshift.resolve(evidence, name_result, self._redshift_tolerance)
        if reason is not None:
            return _pending(redshift_result, reason)
        match_reason = _narrowed_to_existing(
            name_result, redshift_result, CrossmatchReason.MATCHED_REDSHIFT, match_reason
        )

        type_result, reason = object_type.resolve(evidence, redshift_result)
        if reason is not None:
            return _pending(type_result, reason)
        match_reason = _narrowed_to_existing(redshift_result, type_result, CrossmatchReason.MATCHED_TYPE, match_reason)

        if isinstance(type_result, PreliminaryNew):
            return CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED)
        if isinstance(type_result, PreliminaryExisting):
            return CrossmatchResult(
                status=CrossmatchStatus.EXISTING,
                triage_status=TriageStatus.RESOLVED,
                matched_pgc=type_result.pgc,
                reason=match_reason,
            )
        return CrossmatchResult(
            status=CrossmatchStatus.COLLIDING,
            triage_status=TriageStatus.PENDING,
            colliding_pgcs=list(type_result.pgcs),
            reason=CrossmatchReason.MULTIPLE_OBJECTS_MATCHED,
        )
