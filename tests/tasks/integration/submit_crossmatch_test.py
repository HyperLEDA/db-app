from typing import Any
from uuid import UUID, uuid4

import pytest
import structlog

from app import tasks
from app.lib.crossmatch import data as crossmatch_data
from app.lib.crossmatch.models import Parameter
from app.lib.storage import enums, postgres
from app.tasks.submit_crossmatch.task import SubmitCrossmatchTask
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _pgc(storage: postgres.PgStorage, record_id: str) -> int | None:
    return storage.query_one("SELECT pgc FROM layer0.records WHERE id = %s", params=[record_id])["pgc"]


def test_submit_crossmatch_assigns_pgcs(pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = pg_storage.storage
    table_name = "submit_task"
    new_id = str(uuid4())
    existing_id = str(uuid4())
    pending_existing_id = str(uuid4())
    collided_id = str(uuid4())
    bib_id = layer_seed.create_bibliography(storage, table_name, 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, [new_id, existing_id, pending_existing_id, collided_id])
    layer_seed.register_pgcs(storage, [42, 8, 9])
    crossmatch_data.write_crossmatch_rows(
        storage,
        [
            (new_id, enums.RecordTriageStatus.RESOLVED, []),
            (existing_id, enums.RecordTriageStatus.RESOLVED, [42]),
            (pending_existing_id, enums.RecordTriageStatus.PENDING, [42]),
            (collided_id, enums.RecordTriageStatus.PENDING, [8, 9]),
        ],
    )
    tables: list[list[dict[str, object]]] = []

    def create_table(**kwargs: Any) -> UUID:
        tables.append(kwargs["table"])
        return UUID(int=2)

    monkeypatch.setattr("prefect.artifacts.create_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.update_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.create_table_artifact", create_table)
    task = SubmitCrossmatchTask(structlog.get_logger(), {"table_name": table_name, "batch_size": 1})
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
        new_pgc = _pgc(storage, new_id)
        assert new_pgc is not None and new_pgc != 42
        assert _pgc(storage, existing_id) == 42
        assert _pgc(storage, pending_existing_id) == 42
        assert _pgc(storage, collided_id) is None
        assert tables[-1] == [
            {"outcome": "submitted", "count": 3},
            {"outcome": "new", "count": 1},
            {"outcome": "existing", "count": 2},
        ]
        pgc_count = storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"]
        task.run()
    finally:
        task.cleanup()
    assert _pgc(storage, new_id) == new_pgc
    assert storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"] == pgc_count
    assert tables[-1][0]["count"] == 0


def test_submit_crossmatch_requires_parameters(
    pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = pg_storage.storage
    table_name = "submit_task_params"
    new_id = str(uuid4())
    matched_id = str(uuid4())
    weak_id = str(uuid4())
    bib_id = layer_seed.create_bibliography(storage, table_name, 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, [new_id, matched_id, weak_id])
    layer_seed.register_pgcs(storage, [42, 43])
    crossmatch_data.write_crossmatch_rows(
        storage,
        [
            (new_id, enums.RecordTriageStatus.RESOLVED, []),
            (
                matched_id,
                enums.RecordTriageStatus.RESOLVED,
                [(42, {Parameter.COORDINATES: True, Parameter.NAME: True})],
            ),
            (
                weak_id,
                enums.RecordTriageStatus.RESOLVED,
                [(43, {Parameter.COORDINATES: True, Parameter.NAME: False})],
            ),
        ],
    )
    monkeypatch.setattr("prefect.artifacts.create_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.update_progress_artifact", lambda **_: UUID(int=1))
    monkeypatch.setattr("prefect.artifacts.create_table_artifact", lambda **_: UUID(int=2))
    task = SubmitCrossmatchTask(
        structlog.get_logger(),
        {
            "table_name": table_name,
            "batch_size": 10,
            "include_new": True,
            "include_existing": True,
            "require_parameters": ["coordinates", "name"],
        },
    )
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    assert _pgc(storage, new_id) is not None
    assert _pgc(storage, matched_id) == 42
    assert _pgc(storage, weak_id) is None
