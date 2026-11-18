from app.lib.crossmatch.models import CrossmatchReason, RecordEvidence
from app.lib.crossmatch.preliminary import (
    PreliminaryColliding,
    PreliminaryExisting,
    PreliminaryNew,
    PreliminaryStatus,
)


def resolve(evidence: RecordEvidence, radius_deg: float) -> tuple[PreliminaryStatus, CrossmatchReason | None]:
    neighbors_within_radius = [n for n in evidence.neighbors if n.distance_deg <= radius_deg]
    if len(neighbors_within_radius) == 0:
        return PreliminaryNew(), None
    if len(neighbors_within_radius) == 1:
        return PreliminaryExisting(neighbors_within_radius[0].pgc), None
    return PreliminaryColliding({n.pgc for n in neighbors_within_radius}), None
