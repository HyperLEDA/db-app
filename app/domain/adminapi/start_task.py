from collections.abc import Callable
from typing import Any

from app import entities, schema
from app.commands.adminapi import depot
from app.domain import tasks
from app.lib.web.errors import NotFoundError

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


def start_task(dpt: depot.Depot, r: schema.StartTaskRequest) -> schema.StartTaskResponse:
    if r.task_name not in TASK_REGISTRY:
        raise NotFoundError(f"unable to find task '{r.task_name}'")

    task, params_type = TASK_REGISTRY[r.task_name]

    params = params_type(**r.payload)

    with dpt.common_repo.with_tx():
        task_id = dpt.common_repo.insert_task(entities.Task(r.task_name, r.payload, 1))
        dpt.queue_repo.enqueue(
            tasks.task_runner,
            func=task,
            task_id=task_id,
            params=params,
        )

    return schema.StartTaskResponse(task_id)
