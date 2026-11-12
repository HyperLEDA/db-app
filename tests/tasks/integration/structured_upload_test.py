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
    db.exec("DELETE FROM common.pgc_changes")
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
    touched = pg_storage.storage.query(
        "SELECT pgc FROM common.pgc_changes WHERE pgc = %s",
        params=[pgc],
    )
    assert stored == [{"record_id": "r1", "design": "NGC 905"}]
    assert modified["modification_dt"].year != 2000
    assert len(touched) == 1


def _seed_bulk(storage: PostgresTestStorage, table_name: str, count: int) -> list[str]:
    db = storage.storage
    bib_id = layer_seed.create_bibliography(db, f"bib-{table_name}", 2000, ["test"], "test")
    layer_seed.create_table(db, table_name, bib_id)
    table = sql.Identifier("rawdata", table_name)
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN hyperleda_internal_id text").format(table))
    db.exec(sql.SQL("ALTER TABLE {} ADD COLUMN design text").format(table))
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


def _run_spied(
    pg_storage: PostgresTestStorage, table_name: str, monkeypatch: pytest.MonkeyPatch, batch_size: int
) -> list[list[str]]:
    batches: list[list[str]] = []
    original = repository.Repository.fetch_rawdata_pages

    def spy(self: repository.Repository, *args: object, **kwargs: object) -> list[dict[str, object]]:
        rows = original(self, *args, **kwargs)  # type: ignore[arg-type]
        batches.append([str(row["hyperleda_internal_id"]) for row in rows])
        return rows

    monkeypatch.setattr(repository.Repository, "fetch_rawdata_pages", spy)
    repo = repository.Repository(pg_storage.storage, structlog.get_logger())
    params = _params(repo, table_name, write=False)
    params["batch_size"] = batch_size
    task = structured_upload.StructuredCatalogUploadTask(structlog.get_logger(), layer1.Catalog.DESIGNATION, params)
    task.prepare(tasks.Config(storage=pg_storage.config))
    try:
        task.run()
    finally:
        task.cleanup()
    return batches


def test_every_row_is_read_exactly_once_across_batches(
    pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _seed_bulk(pg_storage, "upload_bulk", 300)
    batches = _run_spied(pg_storage, "upload_bulk", monkeypatch, batch_size=30)
    assert len(batches) > 3
    assert sorted(i for batch in batches for i in batch) == ids


def test_empty_page_range_in_the_middle_does_not_stop_reading(
    pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _seed_bulk(pg_storage, "upload_gap", 300)
    pg_storage.storage.exec(
        "DELETE FROM rawdata.upload_gap WHERE hyperleda_internal_id BETWEEN 'r000050' AND 'r000200'"
    )
    batches = _run_spied(pg_storage, "upload_gap", monkeypatch, batch_size=30)
    empty_index = next(i for i, batch in enumerate(batches) if not batch)
    assert any(batches[empty_index + 1 :])
    expected = [i for i in ids if not "r000050" <= i <= "r000200"]
    assert sorted(i for batch in batches for i in batch) == expected


def test_table_names_requiring_quoting(pg_storage: PostgresTestStorage, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ["J_A+A_682_4_lsb", "siena_galaxy_atlas_2026-03-07", "Mixed Case"]:
        ids = _seed_bulk(pg_storage, name, 100)
        batches = _run_spied(pg_storage, name, monkeypatch, batch_size=30)
        assert sorted(i for batch in batches for i in batch) == ids


def test_page_stats_fall_back_to_count_when_never_analyzed(pg_storage: PostgresTestStorage) -> None:
    ids = _seed_bulk(pg_storage, "upload_unanalyzed", 300)
    stats = pg_storage.storage.query_one(
        "SELECT reltuples FROM pg_class WHERE oid = 'rawdata.upload_unanalyzed'::regclass"
    )
    assert stats["reltuples"] <= 0
    repo = repository.Repository(pg_storage.storage, structlog.get_logger())
    pages, rows_per_page = repo.get_rawdata_page_stats("upload_unanalyzed")
    assert pages > 1
    assert rows_per_page == pytest.approx(len(ids) / pages)
