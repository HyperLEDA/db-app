from app.tasks.crossmatch.models import PendingReason, RecordEvidence
from app.tasks.crossmatch.preliminary import PreliminaryExisting, PreliminaryNew, PreliminaryStatus

SIMILAR_TYPE_MAP = {
    "G": {"ext", "?", "QSO"},
    "ext": {"G", "?", "QSO"},
}


def _types_match(record_type: str, other_type: str) -> bool:
    return record_type == other_type or other_type in SIMILAR_TYPE_MAP.get(record_type, set())


def resolve(evidence: RecordEvidence, previous: PreliminaryStatus) -> tuple[PreliminaryStatus, PendingReason | None]:
    if evidence.record_type_name is None:
        return previous, None
    if isinstance(previous, PreliminaryNew):
        return previous, None

    record_type = evidence.record_type_name
    if isinstance(previous, PreliminaryExisting):
        neighbor = next((n for n in evidence.neighbors if n.pgc == previous.pgc), None)
        existing_type = neighbor.type_name if neighbor is not None else None
        if existing_type is not None and not _types_match(record_type, existing_type):
            return previous, PendingReason.TYPE_MISMATCH
        return previous, None

    same_type_neighbors = [
        n
        for n in evidence.neighbors
        if n.pgc in previous.pgcs and n.type_name is not None and _types_match(record_type, n.type_name)
    ]
    if len(same_type_neighbors) == 1:
        return PreliminaryExisting(same_type_neighbors[0].pgc), None
    return previous, None
