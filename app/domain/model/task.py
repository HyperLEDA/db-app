from dataclasses import dataclass
from typing import Any


@dataclass
class StartTaskRequest:
    task_name: str
    payload: dict[str, Any]


@dataclass
class StartTaskResponse:
    id: int
