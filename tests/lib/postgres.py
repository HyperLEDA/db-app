import atexit
import pathlib
import sys

import psycopg
import structlog
from testcontainers import postgres as pgcontainer

from app.lib.storage import postgres
from tests.lib import web

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

_test_storage: "TestPostgresStorage | None" = None


def exit_handler():
    global _test_storage
    if _test_storage is not None:
        logger.info("Stopping postgres container")
        _test_storage.stop()


def debug_enabled() -> bool:
    try:
        if sys.gettrace() is not None:
            return True
    except AttributeError:
        pass

    try:
        if sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID) is not None:
            return True
    except AttributeError:
        pass

    return False


class TestPostgresStorage:
    def __init__(self, migrations_dir: str) -> None:
        self.need_new_container = not debug_enabled()

        if self.need_new_container:
            self.config = self._init_new_container()
        else:
            self.config = postgres.PgStorageConfig(
                endpoint="localhost",
                port=6432,
                user="hyperleda",
                password="password",
                dbname="hyperleda",
            )

        self.storage = postgres.PgStorage(self.config, logger)

        self.migrations_dir = migrations_dir

    def _init_new_container(self) -> postgres.PgStorageConfig:
        self.port = web.find_free_port()
        logger.info("Initializing postgres container", port=self.port)
        try:
            self.container = pgcontainer.PostgresContainer(
                "postgis/postgis:17-3.5-alpine@sha256:f63cf3c8acfd305a5b33d34b2667509b53465924999fe2ec276166080c16319b",
                port=5432,
                user="hyperleda",
                password="password",
                dbname="hyperleda",
            ).with_bind_ports(5432, self.port)
        except Exception as e:
            raise RuntimeError("Failed to start postgres container. Did you forget to start Docker daemon?") from e

        return postgres.PgStorageConfig(
            endpoint="localhost",
            port=self.port,
            user="hyperleda",
            password="password",
            dbname="hyperleda",
        )

    @staticmethod
    def get() -> "TestPostgresStorage":
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

    def _run_migrations(self, migrations_dir: str):
        connection = psycopg.connect(self.config.get_dsn(), autocommit=True)

        migrations = list(pathlib.Path(migrations_dir).iterdir())
        migrations.sort()
        cur = connection.cursor()

        for migration_filename in migrations:
            data = pathlib.Path(migration_filename).read_text()
            logger.info(f"running {migration_filename} migration")
            cur.execute(data.encode("utf-8"))

        connection.commit()
        cur.close()
        connection.close()

    def clear(self):
        if not self.need_new_container:
            return

        self.storage.exec("TRUNCATE common.bib CASCADE")
        self.storage.exec("TRUNCATE rawdata.tables CASCADE")
        tables = self.storage.query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'rawdata' AND table_name NOT IN ('tables', 'pgc', 'objects', 'crossmatch')
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
        if self.need_new_container:
            self.container.start()
            self._run_migrations(self.migrations_dir)
        self.storage.connect()

    def stop(self):
        self.storage.disconnect()
        if self.need_new_container:
            self.container.stop()
