import enum


class TaskStatus(enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    DONE = "done"
