import enum


class TaskStatus(enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    DONE = "done"


class DataType(enum.Enum):
    REGULAR = "regular"
    REPROCESSING = "reprocessing"
    PRELIMINARY = "preliminary"
    COMPILATION = "compilation"


class RawDataStatus(enum.Enum):
    INITIATED = "initiated"
    DOWNLOADING = "downloading"
    FAILED = "failed"
    DOWNLOADED = "downloaded"
    AUTO_X_ID = "auto x-id"
    AUTO_X_ID_FINISHED = "auto x-id finished"
    MANUAL_X_ID = "manual x-id"
    PROCESSED = "processed"


class ObjectCrossmatchStatus(str, enum.Enum):
    UNPROCESSED = "unprocessed"
    NEW = "new"
    COLLIDED = "collided"
    EXISTING = "existing"
