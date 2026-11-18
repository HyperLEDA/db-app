from typing import Any
from uuid import UUID

import pytest
import structlog

from app import tasks
from app.lib.storage import postgres
from app.tasks.crossmatch.task import CrossmatchTask
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _seed(storage: postgres.PgStorage, table_name: str) -> None:
    bib_id = layer_seed.create_bibliography(storage, f"bib-{table_name}", 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, ["near", "far"])
    layer_seed.register_pgcs(storage, [100])
    layer_seed.save_structured_data(
        storage,
        "icrs.data",
        ["ra", "e_ra", "dec", "e_dec"],
        ["near", "far"],
        [[10.0, 0.1, 20.0, 0.1], [180.0, 0.1, 0.0, 0.1]],
    )
    storage.exec(
        "INSERT INTO layer2.objects (pgc, name, ra, dec) VALUES (%s, %s, %s, %s)",
        params=[100, "NGC 1", 10.0, 20.0],
    )
    storage.exec(
        "UPDATE layer0.tables SET modification_dt = TIMESTAMP '2000-01-01' WHERE table_name = %s",
        params=[table_name],
    )


def _run(
    pg_storage: PostgresTestStorage,
    table_name: str,
    *,
    write: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> list[list[dict[str, object]]]:
    tables: list[list[dict[str, object]]] = []
    artifact_id = UUID(int=1)

    def create_progress(**_kwargs: Any) -> UUID:
        return artifact_id

    def create_table(**kwargs: Any) -> UUID:
        tables.append(kwargs["table"])
        return UUID(int=2)

    monkeypatch.setattr("prefect.artifacts.create_progress_artifact", create_progress)
    monkeypatch.setattr("prefect.artifacts.update_progress_artifact", create_progress)
    monkeypatch.setattr("prefect.artifacts.create_table_artifact", create_table)
    task = CrossmatchTask(
        structlog.get_logger(),
        {"table_name": table_name, "radius": 30.0, "write": write, "batch_size": 10},
    )
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    return tables


@pytest.mark.parametrize("write", [False, True])
def test_crossmatch_dry_run_and_write(
    pg_storage: PostgresTestStorage,
    write: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table_name = f"xmatch_{'write' if write else 'dry'}"
    _seed(pg_storage.storage, table_name)
    tables = _run(pg_storage, table_name, write=write, monkeypatch=monkeypatch)
    stored = pg_storage.storage.query(
        "SELECT record_id, triage_status::text AS triage, metadata FROM layer0.crossmatch ORDER BY record_id"
    )
    modified = pg_storage.storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    assert tables[-1][0]["count"] + tables[-1][1]["count"] == 2
    if write:
        assert stored == [
            {"record_id": "far", "triage": "resolved", "metadata": {}},
            {"record_id": "near", "triage": "resolved", "metadata": {"pgc": 100}},
        ]
        assert modified["modification_dt"].year != 2000
    else:
        assert stored == []
        assert modified["modification_dt"].year == 2000
