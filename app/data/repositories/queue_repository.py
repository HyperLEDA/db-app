from typing import Any, Callable

import structlog

from app.data import interface
from app.lib.storage import redis
from app.lib.storage.postgres.config import PgStorageConfig


class QueueRepository(interface.QueueRepository):
    def __init__(
        self,
        queue: redis.RedisQueue,
        pg_config: PgStorageConfig,
        logger: structlog.BoundLogger,
    ) -> None:
        self._queue = queue
        self._storage_config = pg_config
        self._logger = logger

    def enqueue(self, job: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        self._queue.enqueue(job, *args, **kwargs)
