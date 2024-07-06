from typing import Any, Callable

from app import commands
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain import tasks
from app.lib.exceptions import new_not_found_error

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


def start_task(depot: commands.Depot, r: domain_model.StartTaskRequest) -> domain_model.StartTaskResponse:
    if r.task_name not in TASK_REGISTRY:
        raise new_not_found_error(f"unable to find task '{r.task_name}'")

    task, params_type = TASK_REGISTRY[r.task_name]

    params = params_type(**r.payload)

    with depot.common_repo.with_tx() as tx:
        task_id = depot.common_repo.insert_task(data_model.Task(r.task_name, r.payload, 1), tx)
        depot.queue_repo.enqueue(
            tasks.task_runner,
            func=task,
            task_id=task_id,
            params=params,
        )

    return domain_model.StartTaskResponse(task_id)
