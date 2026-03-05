from typing import Any

import structlog

from app.tasks import (
    crossmatch,
    interface,
    layer0_marking,
    layer2_import,
    layer2_import_icrs,
    layer2_import_nature,
    layer2_import_redshift,
    layer2_orphan_cleanup,
    submit_crossmatch,
)

tasks: list[type[interface.Task]] = [
    crossmatch.CrossmatchTask,
    layer0_marking.Layer0MarkingTask,
    submit_crossmatch.SubmitCrossmatchTask,
    layer2_import.Layer2ImportTask,
    layer2_import_icrs.Layer2ImportICRSTask,
    layer2_import_nature.Layer2ImportNatureTask,
    layer2_import_redshift.Layer2ImportRedshiftTask,
    layer2_orphan_cleanup.Layer2OrphanCleanupTask,
]

task_by_name = {task.name(): task for task in tasks}


def list_tasks() -> list[str]:
    return [task.name() for task in tasks]


def get_task(task_name: str, logger: structlog.stdlib.BoundLogger, params: dict[str, Any]) -> interface.Task:
    if task_name not in task_by_name:
        raise ValueError(f"Unknown task: {task_name}")

    params["logger"] = logger

    return task_by_name[task_name](**params)
