from typing import Any
from uuid import UUID

import pytest
import structlog

from app import tasks
from app.tasks.crossmatch.task import CrossmatchTask
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def test_crossmatch_writes_results(pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch) -> None:
    table_name = "xmatch_write"
    layer_seed.seed_crossmatch_preview_table(pg_storage.storage, table_name)
    tables: list[list[dict[str, object]]] = []

    def create_table(**kwargs: Any) -> UUID:
        tables.append(kwargs["table"])
        return UUID(int=2)

    monkeypatch.setattr("prefect.artifacts.create_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.update_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.create_table_artifact", create_table)
    task = CrossmatchTask(
        structlog.get_logger(),
        {"table_name": table_name, "radius_arcsec": 30.0, "batch_size": 10},
    )
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    stored = pg_storage.storage.query(
        "SELECT record_id, triage_status::text AS triage, metadata FROM layer0.crossmatch ORDER BY record_id"
    )
    modified = pg_storage.storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    assert tables[-1][0]["count"] + tables[-1][1]["count"] == 2
    assert stored == [
        {"record_id": "far", "triage": "resolved", "metadata": {}},
        {"record_id": "near", "triage": "pending", "metadata": {"pgc": 100}},
    ]
    assert modified["modification_dt"].year != 2000
