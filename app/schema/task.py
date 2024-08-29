import datetime
from dataclasses import dataclass
from typing import Any


@dataclass
class StartTaskRequest:
    task_name: str
    payload: dict[str, Any]


@dataclass
class StartTaskResponse:
    id: int


@dataclass
class GetTaskInfoRequest:
    task_id: int


@dataclass
class GetTaskInfoResponse:
    id: int | None
    task_name: str
    status: str
    payload: dict[str, Any]
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    message: dict[str, Any] | None
