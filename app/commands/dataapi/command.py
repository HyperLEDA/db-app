import time
from typing import final

import structlog

from app.commands.dataapi import config
from app.lib import commands
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class RunDataAPIServer(commands.Command):
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def prepare(self):
        self.config = config.parse_config(self.config_path)

        self.pg_storage = postgres.PgStorage(self.config.storage, log)
        self.pg_storage.connect()

    def run(self):
        time.sleep(10)

    def cleanup(self):
        self.pg_storage.disconnect()
