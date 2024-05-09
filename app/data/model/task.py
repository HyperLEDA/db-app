import datetime
from dataclasses import dataclass
from typing import Any

from app.lib.storage import enums


@dataclass
class Task:
    task_name: str
    payload: dict[str, Any]
    user_id: int
    status: enums.TaskStatus = enums.TaskStatus.NEW
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    id: int | None = None
    message: dict[str, Any] | None = None
