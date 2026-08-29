import enum


class DataType(enum.Enum):
    REGULAR = "regular"
    REPROCESSING = "reprocessing"
    PRELIMINARY = "preliminary"
    COMPILATION = "compilation"


class RecordCrossmatchStatus(enum.StrEnum):
    UNPROCESSED = "unprocessed"
    NEW = "new"
    COLLIDED = "collided"
    EXISTING = "existing"


class RecordTriageStatus(enum.StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"


class TableStatus(enum.StrEnum):
    INITIATED = "initiated"
    ARCHIVED = "archived"


PG_ENUM_REGISTRY: list[tuple[type[enum.Enum], str]] = [
    (DataType, "common.datatype"),
    (RecordTriageStatus, "layer0.triage_status"),
    (TableStatus, "rawdata.status"),
]
