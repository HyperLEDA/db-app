from typing import Any, Callable

from app import commands, entities, schema
from app.domain import tasks
from app.lib.web.errors import NotFoundError

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


def start_task(depot: commands.Depot, r: schema.StartTaskRequest) -> schema.StartTaskResponse:
    if r.task_name not in TASK_REGISTRY:
        raise NotFoundError(f"unable to find task '{r.task_name}'")

    task, params_type = TASK_REGISTRY[r.task_name]

    params = params_type(**r.payload)

    with depot.common_repo.with_tx() as tx:
        task_id = depot.common_repo.insert_task(entities.Task(r.task_name, r.payload, 1), tx)
        depot.queue_repo.enqueue(
            tasks.task_runner,
            func=task,
            task_id=task_id,
            params=params,
        )

    return schema.StartTaskResponse(task_id)
