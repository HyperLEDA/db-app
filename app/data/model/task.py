import datetime
import enum
from dataclasses import dataclass
from typing import Any


class TaskStatus(enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    DONE = "done"


@dataclass
class Task:
    task_name: str
    payload: dict[str, Any]
    user_id: int
    status: TaskStatus = TaskStatus.NEW
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    id: int | None = None
