import functools
from typing import Any, Callable

import redis
import rq
import structlog

from app.lib.storage.redis import config


class RedisQueue:
    def __init__(self, cfg: config.QueueConfig, logger: structlog.stdlib.BoundLogger) -> None:
        self._config = cfg
        self._logger = logger

    def connect(self) -> None:
        self._logger.debug("connecting to Redis", endpoint=self._config.endpoint, port=self._config.port)
        self._connection = redis.Redis(host=self._config.endpoint, port=self._config.port)
        self._connection.ping()
        self._queue = rq.Queue(self._config.queue_name, connection=self._connection)

    def disconnect(self) -> None:
        if self._connection is not None:
            self._logger.debug("disconnecting from Redis", endpoint=self._config.endpoint, port=self._config.port)
            self._connection.close()

    def get_connection(self) -> redis.Redis:
        return self._connection

    def enqueue(self, job: Callable[..., None], *args: Any, **kwargs) -> None:
        if self._connection is None:
            raise RuntimeError("Unable to enqueue task: connection to Redis was not established")

        self._logger.debug("enqueueing task", args=args, kwargs=kwargs)
        self._queue.enqueue(job, *args, **kwargs)

    def clear_queue(self) -> None:
        if self._connection is None:
            raise RuntimeError("Unable to clear queue: connection to Redis was not established")

        self._logger.debug("clearing queue")
        self._queue.empty()
