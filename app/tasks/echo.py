from typing import final

import structlog

from app.tasks import interface


@final
class EchoTask(interface.Task):
    def __init__(self, message: str = "Test message") -> None:
        self.message = message

    @classmethod
    def name(cls):
        return "echo"

    def prepare(self, config_path: str):
        structlog.get_logger().info("Preparing")

    def run(self):
        structlog.get_logger().info("Running", message=self.message)

    def cleanup(self):
        structlog.get_logger().info("Cleaning up")
