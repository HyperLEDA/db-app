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


class QueueConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = fields.Int(required=True)

    @post_load
    def make(self, data, **kwargs):
        return QueueConfig(**data)


class QueueRepository(interface.QueueRepository):
    def __init__(
        self,
        config: QueueConfig,
        queue_name: str,
        logger: structlog.BoundLogger,
    ) -> None:
        connection = redis.Redis(host=config.endpoint, port=config.port)
        self._queue = rq.Queue(queue_name, connection=connection)
        self._logger = logger

    def enqueue(self, func: Callable[..., None], *args: Any) -> None:
        self._logger.info("starting task", func=func.__name__, args=args)
        self._queue.enqueue(func, *args)
