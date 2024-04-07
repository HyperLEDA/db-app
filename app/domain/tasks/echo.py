import queue
import time
from dataclasses import dataclass

import structlog

from app.data import repositories
from app.lib.storage import postgres
from app.lib import queue


@dataclass
class EchoTaskParams:
    sleep_time_seconds: int


def echo_task(
    task_id: int,
    storage_config: postgres.PgStorageConfig,
    params: EchoTaskParams,
) -> None:
    storage = postgres.PgStorage(storage_config, structlog.get_logger())
    storage.connect()
    repo = repositories.CommonRepository(storage, structlog.get_logger())
    repo.set_task_status(task_id, queue.TaskStatus.IN_PROGRESS)

    print(f"sleeping for {params.sleep_time_seconds} seconds")
    time.sleep(params.sleep_time_seconds)
    print("done!")

    repo.set_task_status(task_id, queue.TaskStatus.DONE)
    storage.disconnect()
