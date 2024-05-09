from typing import Any, Callable

import structlog

from app.data import repositories
from app.lib.storage import enums, postgres


def task_runner(
    func: Callable[[postgres.PgStorage, Any, structlog.stdlib.BoundLogger], None],
    task_id: int,
    storage_config: postgres.PgStorageConfig,
    params: Any,
):
    logger: structlog.stdlib.BoundLogger = structlog.get_logger()
    storage = postgres.PgStorage(storage_config, logger)
    storage.connect()
    repo = repositories.CommonRepository(storage, logger)
    repo.set_task_status(task_id, enums.TaskStatus.IN_PROGRESS)

    try:
        func(storage, params, logger)
    except Exception as e:
        logger.exception(e)
        repo.fail_task(
            task_id,
            {
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        storage.disconnect()
        return

    repo.set_task_status(task_id, enums.TaskStatus.DONE)
    storage.disconnect()
