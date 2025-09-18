from typing import Any

import structlog

from app.tasks import crossmatch, interface, layer0_marking, layer1_import, layer2_import

tasks: list[type[interface.Task]] = [
    crossmatch.CrossmatchTask,
    layer0_marking.Layer0Marking,
    layer1_import.Layer1ImportTask,
    layer2_import.Layer2ImportTask,
]

task_by_name = {task.name(): task for task in tasks}


def list_tasks() -> list[str]:
    return [task.name() for task in tasks]


def get_task(task_name: str, logger: structlog.stdlib.BoundLogger, params: dict[str, Any]) -> interface.Task:
    if task_name not in task_by_name:
        raise ValueError(f"Unknown task: {task_name}")

    params["logger"] = logger

    return task_by_name[task_name](**params)
