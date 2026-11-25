import argparse
import pathlib

import click
import pgmigrate
import psycopg
import sqlparse.engine.grouping as sqlparse_grouping

from app.lib.storage.postgres.config import PgStorageConfig

_LOCK_KEY = 7523669108477809012


def apply(config: PgStorageConfig) -> None:
    base_dir = _base_dir()
    # Own session so the lock stays held while pgmigrate opens another connection for nontransactional migrations.
    with psycopg.connect(config.get_dsn(), autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            _run(config, base_dir)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))


def _base_dir() -> pathlib.Path:
    for parent in pathlib.Path(__file__).resolve().parents:
        if (parent / "postgres" / "migrations").is_dir():
            return parent / "postgres"
    raise RuntimeError("postgres/migrations directory not found")


def _run(config: PgStorageConfig, base_dir: pathlib.Path) -> None:
    sqlparse_grouping.MAX_GROUPING_DEPTH = None
    sqlparse_grouping.MAX_GROUPING_TOKENS = None
    args = argparse.Namespace(
        target="latest",
        conn=config.get_dsn(),
        base_dir=str(base_dir),
    )
    pg_config = pgmigrate.get_config(str(base_dir), args)
    try:
        pgmigrate.migrate(pg_config)
    finally:
        conn = pg_config.conn_instance
        if conn is not None and conn.closed == 0:
            conn.close()


@click.command(short_help="Apply database migrations")
def main() -> None:
    apply(PgStorageConfig())
