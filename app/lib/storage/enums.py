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
