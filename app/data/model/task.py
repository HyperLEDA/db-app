import datetime
from dataclasses import dataclass
from typing import Any

from app.lib import queue


@dataclass
class Task:
    task_name: str
    payload: dict[str, Any]
    user_id: int
    status: queue.TaskStatus = queue.TaskStatus.NEW
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    id: int | None = None
