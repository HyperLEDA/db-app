import os
import pathlib
import socket
from contextlib import closing

import structlog
from testcontainers import postgres

from app import data

log: structlog.stdlib.BoundLogger = structlog.get_logger()


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestPostgresStorage:
    def __init__(self, migrations_dir: str) -> None:
        port = find_free_port()
        log.info("Starting postgres container", port=port)
        self.container = postgres.PostgresContainer(
            "postgres:16",
            port=5432,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        ).with_bind_ports(5432, port)

        self.storage = data.PgStorage(
            data.StorageConfig(
                endpoint="localhost",
                port=port,
                user="hyperleda",
                password="password",
                dbname="hyperleda",
                log_enabled=False,
            )
        )

        self.migrations_dir = migrations_dir

    def _run_migrations(self, migrations_dir: str):
        migrations = os.listdir(migrations_dir)
        migrations.sort()

        for migration_filename in migrations:
            data = pathlib.Path(migrations_dir, migration_filename).read_text()
            # there should be no placeholders in migrations
            data = data.replace("%", "%%")
            self.storage.exec(data, [])

    def clear(self):
        self.storage.exec("TRUNCATE common.pgc CASCADE", [])
        self.storage.exec("TRUNCATE common.bib CASCADE", [])

    def get_storage(self) -> data.PgStorage:
        return self.storage

    def start(self):
        self.container.start()
        self.storage.connect()
        self._run_migrations(self.migrations_dir)

    def stop(self):
        self.storage.disconnect()
        self.container.stop()
