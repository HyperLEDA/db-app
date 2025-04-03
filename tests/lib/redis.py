import atexit

import structlog
from testcontainers import redis as rediscontainer

from app.lib.storage import redis
from tests.lib import web

log: structlog.stdlib.BoundLogger = structlog.get_logger()

_test_storage: "TestRedisStorage | None" = None


def exit_handler():
    global _test_storage
    if _test_storage is not None:
        log.info("Stopping redis container")
        _test_storage.stop()


class TestRedisStorage:
    def __init__(self) -> None:
        self.port = web.find_free_port()
        log.info("Initializing redis container", port=self.port)
        try:
            self.container = rediscontainer.RedisContainer("redis:7").with_bind_ports(6379, self.port)
        except Exception as e:
            raise RuntimeError("Failed to start redis container. Did you forget to start Docker daemon?") from e

        self.config = redis.QueueConfig(endpoint="localhost", port=self.port, queue_name="test_queue")
        self.storage = redis.RedisQueue(self.config, log)

    @staticmethod
    def get() -> "TestRedisStorage":
        global _test_storage
        if _test_storage is None:
            _test_storage = TestRedisStorage()
            log.info("Starting redis container")
            _test_storage.start()

            atexit.register(exit_handler)

        return _test_storage

    def get_storage(self) -> redis.RedisQueue:
        return self.storage

    def clear(self) -> None:
        self.storage.clear_queue()

    def start(self) -> None:
        self.container.start()
        self.storage.connect()

    def stop(self) -> None:
        self.storage.disconnect()
        self.container.stop()
