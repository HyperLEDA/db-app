import structlog

from app import data
from app.domain import model, tasks
from app.domain.tasks.echo import EchoTaskParams
from app.lib.exceptions import new_not_found_error

TASK_REGISTRY = {
    "echo": (tasks.echo_task, EchoTaskParams),
}


class QueueActions:
    def __init__(self, repo: data.QueueRepository, logger: structlog.BoundLogger) -> None:
        self._logger = logger
        self._queue_repo = repo

    def start_task(self, request: model.StartTaskRequest) -> model.StartTaskResponse:
        if request.task_name not in TASK_REGISTRY:
            raise new_not_found_error(f"unknown task {request.task_name}")

        task, params_type = TASK_REGISTRY[request.task_name]
        params = params_type(**request.payload)
        self._queue_repo.enqueue(task, params)

        return model.StartTaskResponse()
