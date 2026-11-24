import enum
from dataclasses import dataclass, field


@dataclass
class Neighbor:
    pgc: int
    ra: float
    dec: float
    distance_deg: float
    design: str | None = None
    redshift: float | None = None
    type_name: str | None = None


@dataclass
class RecordEvidence:
    neighbors: list[Neighbor]
    record_designation: str | None = None
    same_name_pgcs: list[int] | None = None
    record_pgc: int | None = None
    claimed_pgc_exists_in_layer2: bool = False
    record_redshift: float | None = None
    record_type_name: str | None = None


class CrossmatchStatus(enum.StrEnum):
    NEW = "new"
    EXISTING = "existing"
    COLLIDING = "colliding"


class TriageStatus(enum.StrEnum):
    RESOLVED = "resolved"
    PENDING = "pending"


class Parameter(enum.StrEnum):
    COORDINATES = "coordinates"
    NAME = "name"
    PGC = "pgc"
    REDSHIFT = "redshift"
    NATURE = "nature"


type ParameterMatches = dict[Parameter, bool]


@dataclass
class CrossmatchResult:
    status: CrossmatchStatus
    triage_status: TriageStatus
    matched_pgc: int | None = None
    colliding_pgcs: list[int] | None = None
    parameters: ParameterMatches = field(default_factory=dict)
    candidate_matches: list[tuple[int, ParameterMatches]] = field(default_factory=list)


@dataclass
class MatchedRecord:
    record_id: str
    result: CrossmatchResult
    designation: str | None
    ra: float | None
    dec: float | None
    neighbors: list[Neighbor]
