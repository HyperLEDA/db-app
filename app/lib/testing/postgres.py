import atexit
import os
import pathlib

import psycopg
import structlog
from testcontainers import postgres as pgcontainer

from app.lib.storage import postgres
from app.lib.testing import web

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class TestPostgresStorage:
    def __init__(self, migrations_dir: str) -> None:
        self.port = web.find_free_port()
        logger.info("Initializing postgres container", port=self.port)
        self.container = pgcontainer.PostgresContainer(
            "postgis/postgis:17-3.5",
            port=5432,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        ).with_bind_ports(5432, self.port)
        self.config = postgres.PgStorageConfig(
            endpoint="localhost",
            port=self.port,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        )

        self.storage = postgres.PgStorage(self.config, logger)
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
            logger.info(f"running {migration_filename} migration")
            cur.execute(data)

        connection.commit()
        cur.close()
        connection.close()

    def clear(self):
        self.storage.exec("TRUNCATE common.pgc CASCADE")
        self.storage.exec("TRUNCATE common.bib CASCADE")
        self.storage.exec("TRUNCATE rawdata.tables CASCADE")
        tables = self.storage.query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'rawdata' AND table_name NOT IN ('tables', 'objects')
            """)
        for table in tables:
            self.storage.exec(f"DROP TABLE rawdata.{table['table_name']} CASCADE")

        for table in self.storage.query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'layer2'"
        ):
            self.storage.exec(f"TRUNCATE layer2.{table['table_name']} CASCADE")

        self.storage.exec("INSERT INTO layer2.last_update VALUES (to_timestamp(0))")

    def get_storage(self) -> postgres.PgStorage:
        return self.storage

    def start(self):
        self.container.start()
        self._run_migrations(self.migrations_dir)
        self.storage.connect()

    def stop(self):
        self.storage.disconnect()
        self.container.stop()


_test_storage: TestPostgresStorage | None = None


def get_test_postgres_storage() -> TestPostgresStorage:
    """
    Obtains Postgres storage object that may be used for testing.

    It is made efficiently - if the storage was already created (using this function)
    it will not be created again but reused to save time. This requires the caller to clear the
    storage themselves when they need it (by calling `clear()` function of the return value
    of this function).

    Usually caller does not need to stop the containers manually - it will be stopped once the
    process stops (if it happens gracefully, of course).
    """
    global _test_storage
    if _test_storage is None:
        _test_storage = TestPostgresStorage("postgres/migrations")
        logger.info("Starting postgres container")
        _test_storage.start()

        atexit.register(exit_handler)

    return _test_storage


def exit_handler():
    global _test_storage
    if _test_storage is not None:
        logger.info("Stopping postgres container")
        _test_storage.stop()
