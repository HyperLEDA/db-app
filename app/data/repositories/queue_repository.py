from dataclasses import dataclass
from typing import Any, Callable

import redis
import rq
import structlog
from marshmallow import Schema, fields, post_load

from app.data import interface


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
        logger: structlog.BoundLogger,
    ) -> None:
        connection = redis.Redis(host=config.endpoint, port=config.port)
        self._queue = rq.Queue(config.queue_name, connection=connection)
        self._logger = logger

    def enqueue(self, func: Callable[..., None], *args: Any) -> None:
        self._logger.info("starting task", func=func.__name__, args=args)
        self._queue.enqueue(func, *args)
