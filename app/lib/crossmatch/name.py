from app.lib.crossmatch.models import CrossmatchReason, RecordEvidence
from app.lib.crossmatch.preliminary import (
    PreliminaryColliding,
    PreliminaryExisting,
    PreliminaryNew,
    PreliminaryStatus,
)


def resolve(evidence: RecordEvidence, previous: PreliminaryStatus) -> tuple[PreliminaryStatus, CrossmatchReason | None]:
    name_pgcs = set(evidence.same_name_pgcs or [])

    if isinstance(previous, PreliminaryNew):
        if len(name_pgcs) == 0:
            return previous, None
        if len(name_pgcs) == 1:
            objs = evidence.same_name_pgcs or []
            return PreliminaryExisting(objs[0]), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE
        return PreliminaryColliding(name_pgcs), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE

    if isinstance(previous, PreliminaryExisting):
        record_pgc = previous.pgc
        if len(name_pgcs) == 0:
            return previous, None
        if len(name_pgcs) == 1:
            name_pgc = next(iter(name_pgcs))
            if name_pgc == record_pgc:
                return previous, None
            return PreliminaryColliding({name_pgc, record_pgc}), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE
        return PreliminaryColliding(name_pgcs | {record_pgc}), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE

    if len(name_pgcs) == 0:
        return previous, None
    if len(name_pgcs) == 1:
        name_pgc = next(iter(name_pgcs))
        for matched_pgc in previous.pgcs:
            if matched_pgc == name_pgc:
                return PreliminaryExisting(name_pgc), None
        return PreliminaryColliding(previous.pgcs | {name_pgc}), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE

    common_pgcs = name_pgcs.intersection(previous.pgcs)
    if len(common_pgcs) == 1:
        return PreliminaryExisting(next(iter(common_pgcs))), None
    return PreliminaryColliding(previous.pgcs | name_pgcs), CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE
