import json
from collections.abc import Generator

import pytest
import structlog
from psycopg import sql

from app import tasks
from app.tasks import refresh_table_stats
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture
def refresh_task(pg_storage: PostgresTestStorage) -> Generator[refresh_table_stats.RefreshTableStatsTask]:
    task = refresh_table_stats.RefreshTableStatsTask(structlog.get_logger())
    task.prepare(tasks.Config(storage=pg_storage.config))
    yield task
    task.cleanup()


def _statistics(storage: PostgresTestStorage, table_name: str) -> tuple[dict, object, object]:
    row = storage.storage.query_one(
        """
        SELECT modification_dt, statistics_refresh_dt, statistics
        FROM layer0.tables WHERE table_name = %s
        """,
        params=[table_name],
    )
    cache = row["statistics"]
    if isinstance(cache, str):
        cache = json.loads(cache)
    return cache, row["modification_dt"], row["statistics_refresh_dt"]


def test_refresh_updates_only_stale_tables(
    pg_storage: PostgresTestStorage,
    refresh_task: refresh_table_stats.RefreshTableStatsTask,
) -> None:
    storage = pg_storage.storage
    table_name = "refresh_stats"
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, ["r1"])

    storage.exec(
        sql.SQL("ALTER TABLE rawdata.{} ADD COLUMN name text, ADD COLUMN ra double precision").format(
            sql.Identifier(table_name)
        )
    )
    storage.exec(
        sql.SQL("INSERT INTO rawdata.{} (name, ra) VALUES (%s, %s), (%s, %s)").format(sql.Identifier(table_name)),
        params=["a", 1.0, "b", None],
    )

    refresh_task.run()
    cache, modified, refreshed = _statistics(pg_storage, table_name)
    assert cache["total_records"] == 1
    assert cache["columns"] == {
        "name": {"non_null_count": 2, "min": "a", "max": "b"},
        "ra": {"non_null_count": 1, "min": 1.0, "max": 1.0},
    }
    assert refreshed == modified

    storage.exec(
        "UPDATE layer0.tables SET statistics = jsonb_set(statistics, '{total_records}', '99') WHERE table_name = %s",
        params=[table_name],
    )
    refresh_task.run()
    assert _statistics(pg_storage, table_name)[0]["total_records"] == 99

    storage.exec("UPDATE layer0.tables SET modification_dt = now() WHERE table_name = %s", params=[table_name])
    refresh_task.run()
    cache, modified, refreshed = _statistics(pg_storage, table_name)
    assert cache["total_records"] == 1
    assert cache["columns"] == {
        "name": {"non_null_count": 2, "min": "a", "max": "b"},
        "ra": {"non_null_count": 1, "min": 1.0, "max": 1.0},
    }
    assert refreshed == modified
