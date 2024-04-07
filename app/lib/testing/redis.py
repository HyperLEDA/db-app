import structlog
from testcontainers import redis as rediscontainer

from app.lib.storage import redis
from app.lib.testing import common

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class TestRedisStorage:
    def __init__(self) -> None:
        port = common.find_free_port()
        log.info("Initializing redis container", port=port)
        self.container = rediscontainer.RedisContainer("redis:7").with_bind_ports(6379, port)
        self.config = redis.QueueConfig(endpoint="localhost", port=port, queue_name="test_queue")
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
