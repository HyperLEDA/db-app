from dataclasses import dataclass
from typing import Any, Callable

import redis
import rq
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
    def __init__(self, config: QueueConfig) -> None:
        connection = redis.Redis(host=config.endpoint, port=config.port)
        self._queue = rq.Queue(name="default", connection=connection)

    def enqueue(self, func: Callable[..., Any], *args: Any) -> None:
        self._queue.enqueue(func, *args)
