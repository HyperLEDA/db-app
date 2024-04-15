import atexit

import structlog
from testcontainers import redis as rediscontainer

from app.lib.storage import redis
from app.lib.testing import common

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class TestRedisStorage:
    def __init__(self) -> None:
        self.port = common.find_free_port()
        log.info("Initializing redis container", port=self.port)
        self.container = rediscontainer.RedisContainer("redis:7").with_bind_ports(6379, self.port)
        self.config = redis.QueueConfig(endpoint="localhost", port=self.port, queue_name="test_queue")
        self.storage = redis.RedisQueue(self.config, log)

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


_test_storage: TestRedisStorage | None = None


def get_or_create_test_redis_storage() -> TestRedisStorage:
    global _test_storage
    if _test_storage is None:
        _test_storage = TestRedisStorage()
        log.info("Starting redis container")
        _test_storage.start()

        atexit.register(exit_handler)

    return _test_storage


def exit_handler():
    global _test_storage
    if _test_storage is not None:
        log.info("Stopping redis container")
        _test_storage.stop()
