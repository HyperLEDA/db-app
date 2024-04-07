import os
import pathlib
import socket
from contextlib import closing

import psycopg
import structlog
from testcontainers import postgres as pgcontainer

from app.lib.storage import postgres
from app.lib.testing import common

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class TestPostgresStorage:
    def __init__(self, migrations_dir: str) -> None:
        port = common.find_free_port()
        log.info("Initializing postgres container", port=port)
        self.container = pgcontainer.PostgresContainer(
            "postgres:16",
            port=5432,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        ).with_bind_ports(5432, port)
        self.config = postgres.PgStorageConfig(
            endpoint="localhost",
            port=port,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        )

        self.storage = postgres.PgStorage(self.config, log)
        self.migrations_dir = migrations_dir

    def _run_migrations(self, migrations_dir: str):
        connection = psycopg.connect(self.config.get_dsn(), autocommit=True)
        migrations = os.listdir(migrations_dir)
        migrations.sort()
        cur = connection.cursor()

        for migration_filename in migrations:
            data = pathlib.Path(migrations_dir, migration_filename).read_text()
            # ignore placeholders in migrations
            data = data.replace("%", "%%")
            cur.execute(data)

        connection.commit()
        cur.close()
        connection.close()

    def clear(self):
        self.storage.exec("TRUNCATE common.pgc CASCADE", [])
        self.storage.exec("TRUNCATE common.bib CASCADE", [])

    def get_storage(self) -> postgres.PgStorage:
        return self.storage

    def start(self):
        self.container.start()
        self._run_migrations(self.migrations_dir)
        self.storage.connect()

    def stop(self):
        self.storage.disconnect()
        self.container.stop()