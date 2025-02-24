from typing import Any

from app.tasks import echo, interface

tasks = [echo.EchoTask]


def list_tasks() -> list[str]:
    return [task.name() for task in tasks]


def get_task(task_name: str, params: dict[str, Any]) -> interface.Task:
    for task in tasks:
        if task.name() == task_name:
            return task(**params)

    raise ValueError(f"Unknown task: {task_name}")
