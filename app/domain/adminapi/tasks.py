from collections.abc import Callable
from typing import Any

from app.data import repositories
from app.domain import tasks
from app.presentation import adminapi

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


class TaskManager:
    def __init__(self, common_repo: repositories.CommonRepository, queue_repo: repositories.QueueRepository):
        self.common_repo = common_repo
        self.queue_repo = queue_repo

    def get_task_info(self, r: adminapi.GetTaskInfoRequest) -> adminapi.GetTaskInfoResponse:
        task_info = self.common_repo.get_task_info(r.task_id)
        return adminapi.GetTaskInfoResponse(
            task_info.id,
            task_info.task_name,
            str(task_info.status.value),
            task_info.payload,
            task_info.start_time,
            task_info.end_time,
            task_info.message,
        )
