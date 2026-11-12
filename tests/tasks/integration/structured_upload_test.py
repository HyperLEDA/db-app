import pytest
import structlog
from psycopg import sql

from app import tasks
from app.catalogs import layer1
from app.lib.storage import postgres
from app.tasks import repository, structured_upload
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _prepare_raw(db: postgres.PgStorage, table_name: str) -> sql.Identifier:
    bib_id = layer_seed.create_bibliography(db, f"bib-{table_name}", 2000, ["test"], "test")
    layer_seed.create_table(db, table_name, bib_id)
    table = sql.Identifier("rawdata", table_name)
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN hyperleda_internal_id text").format(table))
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN design text").format(table))
    return table


def _seed(storage: PostgresTestStorage, table_name: str) -> int:
    db = storage.storage
    table = _prepare_raw(db, table_name)
    db.exec(
        sql.SQL("INSERT INTO {} (hyperleda_internal_id, design) VALUES (%s, %s), (%s, %s)").format(table),
        params=["r1", "ngc905", "r2", None],
    )
    layer_seed.register_records(db, table_name, ["r1", "r2"])
    layer_seed.register_pgcs(db, [4242])
    db.exec("UPDATE layer0.records SET pgc = %s WHERE id = %s", params=[4242, "r1"])
    db.exec("DELETE FROM common.pgc_changes")
    db.exec(
        "UPDATE layer0.tables SET modification_dt = TIMESTAMP '2000-01-01' WHERE table_name = %s",
        params=[table_name],
    )
    return 4242


def _seed_bulk(storage: PostgresTestStorage, table_name: str, count: int) -> list[str]:
    db = storage.storage
    table = _prepare_raw(db, table_name)
    db.exec(
        sql.SQL(
            "INSERT INTO {} (hyperleda_internal_id, design) "
            "SELECT 'r' || lpad(g::text, 6, '0'), 'ngc' || g || repeat('x', 200) FROM generate_series(1, %s) AS g"
        ).format(table),
        params=[count],
    )
    ids = [f"r{i:06d}" for i in range(1, count + 1)]
    layer_seed.register_records(db, table_name, ids)
    return ids


def _params(repo: repository.Repository, table_name: str, *, write: bool, batch_size: int = 10) -> dict[str, object]:
    schema = structured_upload.build_catalog_schema(repo, layer1.Catalog.DESIGNATION)
    params: dict[str, object] = {"table_name": table_name, "write": write, "batch_size": batch_size}
    for field in schema.fields:
        if field.name == "design":
            params[field.name] = 'col("design")'
        elif field.required:
            params[field.name] = '""'
    return params


def _run(
    pg_storage: PostgresTestStorage,
    table_name: str,
    *,
    write: bool,
    batch_size: int = 10,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> tuple[list[list[dict[str, object]]], list[list[str]]]:
    batches: list[list[str]] = []
    if monkeypatch is not None:
        original = repository.Repository.fetch_rawdata_pages

        def spy(self: repository.Repository, *args: object, **kwargs: object) -> list[dict[str, object]]:
            rows = original(self, *args, **kwargs)
            batches.append([str(row["hyperleda_internal_id"]) for row in rows])
            return rows

        monkeypatch.setattr(repository.Repository, "fetch_rawdata_pages", spy)

    repo = repository.Repository(pg_storage.storage, structlog.get_logger())
    previews: list[list[dict[str, object]]] = []
    task = structured_upload.StructuredCatalogUploadTask(
        structlog.get_logger(),
        layer1.Catalog.DESIGNATION,
        _params(repo, table_name, write=write, batch_size=batch_size),
        on_preview_table=lambda rows, _: previews.append(rows),
    )
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    return previews, batches


@pytest.mark.parametrize("write", [False, True])
def test_schema_dry_run_and_write(pg_storage: PostgresTestStorage, write: bool) -> None:
    if not write:
        repo = repository.Repository(pg_storage.storage, structlog.get_logger())
        names = [f.name for f in structured_upload.build_catalog_schema(repo, layer1.Catalog.DESIGNATION).fields]
        assert "design" in names and "record_id" not in names

    table_name = f"upload_{'write' if write else 'dry'}"
    pgc = _seed(pg_storage, table_name)
    previews, _ = _run(pg_storage, table_name, write=write)
    stored = pg_storage.storage.query("SELECT record_id, design FROM designation.data ORDER BY record_id")
    modified = pg_storage.storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s", params=[table_name]
    )
    if write:
        assert stored == [{"record_id": "r1", "design": "NGC 905"}]
        assert modified["modification_dt"].year != 2000
        assert len(pg_storage.storage.query("SELECT pgc FROM common.pgc_changes WHERE pgc = %s", params=[pgc])) == 1
    else:
        assert stored == [] and previews[0][0]["design"] == "ngc905"
        assert modified["modification_dt"].year == 2000


@pytest.mark.parametrize(
    "table_name", ["upload_bulk", "J_A+A_682_4_lsb", "siena_galaxy_atlas_2026-03-07", "Mixed Case"]
)
def test_batch_reads(pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch, table_name: str) -> None:
    count = 300 if table_name == "upload_bulk" else 100
    ids = _seed_bulk(pg_storage, table_name, count)
    _, batches = _run(pg_storage, table_name, write=False, batch_size=30, monkeypatch=monkeypatch)
    if table_name == "upload_bulk":
        assert len(batches) > 3
    assert sorted(i for batch in batches for i in batch) == ids


def test_empty_pages_and_unanalyzed_stats(pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch) -> None:
    ids = _seed_bulk(pg_storage, "upload_gap", 300)
    pg_storage.storage.exec(
        "DELETE FROM rawdata.upload_gap WHERE hyperleda_internal_id BETWEEN 'r000050' AND 'r000200'"
    )
    _, batches = _run(pg_storage, "upload_gap", write=False, batch_size=30, monkeypatch=monkeypatch)
    empty_index = next(i for i, batch in enumerate(batches) if not batch)
    assert any(batches[empty_index + 1 :])
    assert sorted(i for batch in batches for i in batch) == [i for i in ids if not "r000050" <= i <= "r000200"]

    unanalyzed = _seed_bulk(pg_storage, "upload_unanalyzed", 300)
    assert (
        pg_storage.storage.query_one(
            "SELECT reltuples FROM pg_class WHERE oid = 'rawdata.upload_unanalyzed'::regclass"
        )["reltuples"]
        <= 0
    )
    pages, rows_per_page = repository.Repository(pg_storage.storage, structlog.get_logger()).get_rawdata_page_stats(
        "upload_unanalyzed"
    )
    assert pages > 1 and rows_per_page == pytest.approx(len(unanalyzed) / pages)
