import pytest
import structlog
from psycopg import sql

from app import tasks
from app.catalogs import layer1
from app.tasks import repository, structured_upload
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _seed(storage: PostgresTestStorage, table_name: str) -> int:
    db = storage.storage
    bib_id = layer_seed.create_bibliography(db, f"bib-{table_name}", 2000, ["test"], "test")
    layer_seed.create_table(db, table_name, bib_id)
    table = sql.Identifier("rawdata", table_name)
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN hyperleda_internal_id text").format(table))
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN design text").format(table))
    db.exec(
        sql.SQL("INSERT INTO {} (hyperleda_internal_id, design) VALUES (%s, %s), (%s, %s)").format(table),
        params=["r1", "ngc905", "r2", None],
    )
    layer_seed.register_records(db, table_name, ["r1", "r2"])
    layer_seed.register_pgcs(db, [4242])
    db.exec("UPDATE layer0.records SET pgc = %s WHERE id = %s", params=[4242, "r1"])
    db.exec("UPDATE common.pgc SET modification_time = TIMESTAMP '2000-01-01' WHERE id = %s", params=[4242])
    db.exec(
        "UPDATE layer0.tables SET modification_dt = TIMESTAMP '2000-01-01' WHERE table_name = %s",
        params=[table_name],
    )
    return 4242


def _params(repo: repository.Repository, table_name: str, *, write: bool) -> dict[str, object]:
    schema = structured_upload.build_catalog_schema(repo, layer1.Catalog.DESIGNATION)
    params: dict[str, object] = {"table_name": table_name, "write": write, "batch_size": 10}
    for field in schema.fields:
        if field.name == "design":
            params[field.name] = 'col("design")'
        elif field.required:
            params[field.name] = '""'
    return params


def _run(pg_storage: PostgresTestStorage, table_name: str, *, write: bool) -> list[list[dict[str, object]]]:
    repo = repository.Repository(pg_storage.storage, structlog.get_logger())
    previews: list[list[dict[str, object]]] = []
    task = structured_upload.StructuredCatalogUploadTask(
        structlog.get_logger(),
        layer1.Catalog.DESIGNATION,
        _params(repo, table_name, write=write),
        on_preview_table=lambda rows, _: previews.append(rows),
    )
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    return previews


def test_catalog_schema_lists_writable_designation_columns(pg_storage: PostgresTestStorage) -> None:
    repo = repository.Repository(pg_storage.storage, structlog.get_logger())
    schema = structured_upload.build_catalog_schema(repo, layer1.Catalog.DESIGNATION)
    names = [field.name for field in schema.fields]
    assert "design" in names
    assert "record_id" not in names


def test_dry_run_previews_without_writing(pg_storage: PostgresTestStorage) -> None:
    table_name = "upload_dry_run"
    _seed(pg_storage, table_name)
    previews = _run(pg_storage, table_name, write=False)
    stored = pg_storage.storage.query("SELECT record_id, design FROM designation.data")
    modified = pg_storage.storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    assert stored == []
    assert previews[0][0]["design"] == "ngc905"
    assert modified["modification_dt"].year == 2000


def test_write_normalizes_designation_and_touches_pgc(pg_storage: PostgresTestStorage) -> None:
    table_name = "upload_write"
    pgc = _seed(pg_storage, table_name)
    _run(pg_storage, table_name, write=True)
    stored = pg_storage.storage.query(
        "SELECT record_id, design FROM designation.data ORDER BY record_id",
    )
    modified = pg_storage.storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    touched = pg_storage.storage.query_one(
        "SELECT modification_time FROM common.pgc WHERE id = %s",
        params=[pgc],
    )
    assert stored == [{"record_id": "r1", "design": "NGC 905"}]
    assert modified["modification_dt"].year != 2000
    assert touched["modification_time"].year != 2000
