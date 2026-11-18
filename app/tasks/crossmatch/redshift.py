from app.tasks.crossmatch.models import PendingReason, RecordEvidence
from app.tasks.crossmatch.preliminary import PreliminaryExisting, PreliminaryNew, PreliminaryStatus


def resolve(
    evidence: RecordEvidence,
    previous: PreliminaryStatus,
    redshift_tolerance: float | None,
) -> tuple[PreliminaryStatus, PendingReason | None]:
    if redshift_tolerance is None or evidence.record_redshift is None:
        return previous, None

    record_z = evidence.record_redshift
    if isinstance(previous, PreliminaryNew):
        return previous, None
    if isinstance(previous, PreliminaryExisting):
        neighbor = next((n for n in evidence.neighbors if n.pgc == previous.pgc), None)
        if neighbor is None or neighbor.redshift is None:
            return previous, None
        if abs(neighbor.redshift - record_z) < redshift_tolerance:
            return previous, None
        return previous, PendingReason.REDSHIFT_MISMATCH

    neighbors_involved = [n for n in evidence.neighbors if n.pgc in previous.pgcs]
    if any(n.redshift is None for n in neighbors_involved):
        return previous, None
    close = [
        n for n in neighbors_involved if n.redshift is not None and abs(n.redshift - record_z) < redshift_tolerance
    ]
    if len(close) == 1:
        return PreliminaryExisting(close[0].pgc), None
    return previous, None
