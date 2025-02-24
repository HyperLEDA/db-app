from typing import final

import structlog

from app.tasks import interface


@final
class EchoTask(interface.Task):
    def __init__(self, message: str = "Test message") -> None:
        self.message = message

    @classmethod
    def name(cls) -> str:
        return "echo"

    def prepare(self, config: interface.Config):
        structlog.get_logger().info("Preparing", dbname=config.storage.dbname)

    def run(self):
        structlog.get_logger().info("Running", message=self.message)

    def cleanup(self):
        structlog.get_logger().info("Cleaning up")
