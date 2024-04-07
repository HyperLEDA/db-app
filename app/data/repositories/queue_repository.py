import functools
from dataclasses import dataclass
from typing import Any, Callable

import redis
import rq
import structlog
from marshmallow import Schema, fields, post_load

from app.data import interface
from app.lib.storage.postgres.config import PgStorageConfig


@dataclass
class QueueConfig:
    endpoint: str
    port: int
    queue_name: str


class QueueConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = fields.Int(required=True)
    queue_name = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return QueueConfig(**data)


class QueueRepository(interface.QueueRepository):
    def __init__(
        self,
        config: QueueConfig,
        pg_config: PgStorageConfig,
        logger: structlog.BoundLogger,
    ) -> None:
        connection = redis.Redis(host=config.endpoint, port=config.port)
        self._queue = rq.Queue(config.queue_name, connection=connection)
        self._storage_config = pg_config
        self._logger = logger

    def enqueue(self, task_id: int, func: Callable[..., None], *args: Any) -> None:
        job = functools.partial(func, task_id, self._storage_config)
        self._queue.enqueue(job, *args)
        self._logger.info("enqueued task", func=func.__name__, args=args)
