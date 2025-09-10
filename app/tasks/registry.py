from typing import Any

from app.tasks import crossmatch, interface, layer1_import, layer2_import, process

tasks: list[type[interface.Task]] = [
    crossmatch.CrossmatchTask,
    process.ProcessTask,
    layer1_import.Layer1ImportTask,
    layer2_import.Layer2ImportTask,
]

task_by_name = {task.name(): task for task in tasks}


def list_tasks() -> list[str]:
    return [task.name() for task in tasks]


def get_task(task_name: str, params: dict[str, Any]) -> interface.Task:
    if task_name not in task_by_name:
        raise ValueError(f"Unknown task: {task_name}")

    return task_by_name[task_name](**params)
