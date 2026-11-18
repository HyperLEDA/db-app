from app.lib.crossmatch.models import PendingReason, RecordEvidence
from app.lib.crossmatch.preliminary import (
    PreliminaryColliding,
    PreliminaryExisting,
    PreliminaryNew,
    PreliminaryStatus,
)


def resolve(evidence: RecordEvidence, previous: PreliminaryStatus) -> tuple[PreliminaryStatus, PendingReason | None]:
    if evidence.record_pgc is None:
        return previous, None
    if not evidence.claimed_pgc_exists_in_layer2:
        return previous, PendingReason.UNKNOWN_PGC

    pgc = evidence.record_pgc
    if isinstance(previous, PreliminaryNew):
        return PreliminaryExisting(pgc), PendingReason.MATCHED_PGC_OUTSIDE_CIRCLE
    if isinstance(previous, PreliminaryExisting):
        if pgc == previous.pgc:
            return previous, None
        return PreliminaryColliding({pgc, previous.pgc}), PendingReason.MATCHED_PGC_OUTSIDE_CIRCLE
    if pgc in previous.pgcs:
        return PreliminaryExisting(pgc), None
    return PreliminaryColliding(previous.pgcs | {pgc}), PendingReason.MATCHED_PGC_OUTSIDE_CIRCLE
