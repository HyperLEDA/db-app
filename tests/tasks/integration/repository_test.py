import datetime
import pathlib
from typing import final, override
from unittest import mock

import pytest
import structlog
from astropy import table
from astropy import units as u

from app.catalogs import layer0, layer1, layer2
from app.lib.storage import postgres
from app.tasks import repository
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture(scope="module")
def storage(pg_storage: PostgresTestStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


def _save_layer2_data(repo: repository.Repository, objects: list[layer2.Layer2Object]) -> None:
    by_table: dict[str, list[tuple[int, layer2.CatalogObject]]] = {}
    for obj in objects:
        for catalog_obj in obj.data:
            layer2_table = catalog_obj.table()
            if layer2_table not in by_table:
                by_table[layer2_table] = []
            by_table[layer2_table].append((obj.pgc, catalog_obj))
    for table_name, table_entries in by_table.items():
        if not table_entries:
            continue
        columns = table_entries[0][1].keys()
        qtable_data: dict[str, list[object]] = {"pgc": [pgc for pgc, _ in table_entries]}
        for column in columns:
            qtable_data[column] = [catalog_obj.to_row()[column] for _, catalog_obj in table_entries]
        repo.save(table_name, table.QTable(qtable_data))


def _get_table(storage: postgres.PgStorage, table_name: str) -> int:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    return layer_seed.create_table(storage, table_name, bib_id)


def _insert_nature_data(
    storage: postgres.PgStorage,
    table_name: str,
    record_ids: list[str],
    pgcs: dict[str, int],
    rows: list[list[str]],
) -> None:
    _get_table(storage, table_name)
    layer_seed.register_records(storage, table_name, record_ids)
    layer_seed.register_pgcs(storage, list(pgcs.values()))
    layer_seed.upsert_pgc(storage, pgcs)
    columns = ["type_name"]
    layer_seed.save_structured_data(
        storage,
        layer1.NatureCatalogObject.layer1_table(),
        columns,
        record_ids,
        rows,
    )


def test_get_last_update_time_returns_stored_dt(repo: repository.Repository) -> None:
    dt_icrs = repo.get_last_update_time(layer2.Catalog.ICRS)
    dt_nature = repo.get_last_update_time(layer2.Catalog.NATURE)
    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    assert (dt_icrs if dt_icrs.tzinfo else dt_icrs.replace(tzinfo=datetime.UTC)) == epoch
    assert (dt_nature if dt_nature.tzinfo else dt_nature.replace(tzinfo=datetime.UTC)) == epoch


def test_update_last_update_time_updates_stored_dt(repo: repository.Repository) -> None:
    new_dt = datetime.datetime(2020, 6, 15, 12, 0, 0, tzinfo=datetime.UTC)
    repo.update_last_update_time(new_dt, layer2.Catalog.ICRS)

    got_icrs = repo.get_last_update_time(layer2.Catalog.ICRS)
    assert got_icrs.replace(tzinfo=None) == new_dt.replace(tzinfo=None)
    got_nature = repo.get_last_update_time(layer2.Catalog.NATURE)
    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    assert (got_nature if got_nature.tzinfo else got_nature.replace(tzinfo=datetime.UTC)) == epoch


def test_get_orphaned_pgcs_returns_pgcs_without_layer1_data(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(
        repo,
        [
            layer2.Layer2Object(1, [layer2.DesignationCatalogObject(design="a")]),
            layer2.Layer2Object(2, [layer2.DesignationCatalogObject(design="b")]),
        ],
    )

    orphaned = repo.get_orphaned_pgcs([layer2.Catalog.DESIGNATION])

    assert orphaned.keys() == {"layer2.designation"}
    assert set(orphaned["layer2.designation"]) == {1, 2}


def test_get_orphaned_pgcs_returns_empty_when_layer1_present(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "t1")
    layer_seed.register_records(storage, "t1", ["r1"])
    layer_seed.register_pgcs(storage, [100])
    layer_seed.upsert_pgc(storage, {"r1": 100})
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["r1"],
        [["x"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )
    _save_layer2_data(repo, [layer2.Layer2Object(100, [layer2.DesignationCatalogObject(design="x")])])

    orphaned = repo.get_orphaned_pgcs([layer2.Catalog.DESIGNATION])

    assert orphaned == {"layer2.designation": []}


def test_get_orphaned_pgcs_returns_only_pgcs_without_layer1_data(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "t1")
    layer_seed.register_records(storage, "t1", ["r1"])
    layer_seed.register_pgcs(storage, [100, 200])
    layer_seed.upsert_pgc(storage, {"r1": 100})
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["r1"],
        [["linked"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )
    _save_layer2_data(
        repo,
        [
            layer2.Layer2Object(100, [layer2.DesignationCatalogObject(design="linked")]),
            layer2.Layer2Object(200, [layer2.DesignationCatalogObject(design="orphan")]),
        ],
    )

    orphaned = repo.get_orphaned_pgcs([layer2.Catalog.DESIGNATION])

    assert orphaned.keys() == {"layer2.designation"}
    assert set(orphaned["layer2.designation"]) == {200}


@final
class _DesignationAndNature(layer2.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> layer2.Catalog:
        return layer2.Catalog.DESIGNATION

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.designation"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.DESIGNATION, layer1.Catalog.NATURE]


def test_get_orphaned_pgcs_multi_source_only_when_all_sources_empty(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "desig")
    layer_seed.register_records(storage, "desig", ["r2", "r4d"])
    _get_table(storage, "nat")
    layer_seed.register_records(storage, "nat", ["r3", "r4n"])
    layer_seed.register_pgcs(storage, [1, 2, 3, 4])
    layer_seed.upsert_pgc(storage, {"r2": 2, "r3": 3, "r4d": 4, "r4n": 4})
    layer_seed.save_structured_data(
        storage,
        layer1.DesignationCatalogObject.layer1_table(),
        ["design"],
        ["r2", "r4d"],
        [["only-designation"], ["both"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )
    layer_seed.save_structured_data(
        storage,
        layer1.NatureCatalogObject.layer1_table(),
        ["type_name"],
        ["r3", "r4n"],
        [["G"], ["G"]],
    )
    _save_layer2_data(
        repo,
        [layer2.Layer2Object(pgc, [layer2.DesignationCatalogObject(design="row")]) for pgc in (1, 2, 3, 4)],
    )

    with mock.patch.object(layer2, "get_catalog_object_type", return_value=_DesignationAndNature):
        orphaned = repo.get_orphaned_pgcs([layer2.Catalog.DESIGNATION])

    assert set(orphaned["layer2.designation"]) == {1}


def test_remove_pgcs_removes_specified_pgcs(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(
        repo,
        [
            layer2.Layer2Object(1, [layer2.DesignationCatalogObject(design="d1")]),
            layer2.Layer2Object(2, [layer2.DesignationCatalogObject(design="d2")]),
        ],
    )

    repo.remove_pgcs([layer2.Catalog.DESIGNATION], [1])

    removed = storage.query("SELECT pgc FROM layer2.designation WHERE pgc = %s", params=[1])
    assert removed == []
    remaining = storage.query("SELECT pgc, design FROM layer2.designation WHERE pgc = %s", params=[2])
    assert len(remaining) == 1
    assert remaining[0]["design"] == "d2"


def test_get_new_nature_records_returns_empty_when_no_nature_data(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "empty_table")
    layer_seed.register_records(storage, "empty_table", ["r1"])
    layer_seed.register_pgcs(storage, [100])
    layer_seed.upsert_pgc(storage, {"r1": 100})

    result = repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)
    assert len(result) == 0


def test_get_new_nature_records_returns_all_when_dt_is_epoch(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _insert_nature_data(
        storage,
        "t1",
        ["rec1", "rec2"],
        {"rec1": 1001, "rec2": 1002},
        [["G"], ["QSO"]],
    )

    result = repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), 10, 0)

    assert len(result) == 2
    by_pgc = {int(pgc): str(type_name) for pgc, type_name in zip(result["pgc"], result["type_name"], strict=True)}
    assert by_pgc[1001] == "G"
    assert by_pgc[1002] == "QSO"


def test_get_new_nature_records_returns_empty_when_dt_is_in_future(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _insert_nature_data(
        storage,
        "t1",
        ["rec1"],
        {"rec1": 1001},
        [["G"]],
    )

    future = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
    result = repo.get_new_nature_records(future, 10, 0)

    assert len(result) == 0


def test_get_new_nature_records_respects_limit_and_offset_by_pgc(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _insert_nature_data(
        storage,
        "t1",
        ["r1", "r2", "r3"],
        {"r1": 10, "r2": 20, "r3": 30},
        [["G"], ["*"], ["?"]],
    )
    dt = datetime.datetime.fromtimestamp(0, tz=datetime.UTC)

    first_batch = repo.get_new_nature_records(dt, limit=1, offset=0)
    assert len(first_batch) == 1
    assert int(first_batch["pgc"][0]) == 10
    assert str(first_batch["type_name"][0]) == "G"

    second_batch = repo.get_new_nature_records(dt, limit=1, offset=10)
    assert len(second_batch) == 1
    assert int(second_batch["pgc"][0]) == 20
    assert str(second_batch["type_name"][0]) == "*"

    third_batch = repo.get_new_nature_records(dt, limit=1, offset=20)
    assert len(third_batch) == 1
    assert int(third_batch["pgc"][0]) == 30


def test_get_new_nature_records_returns_all_records_for_same_pgc_in_one_batch(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _insert_nature_data(
        storage,
        "t1",
        ["r1", "r2"],
        {"r1": 99, "r2": 99},
        [["G"], ["*"]],
    )

    result = repo.get_new_nature_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), limit=10, offset=0)

    assert len(result) == 2
    assert {int(pgc) for pgc in result["pgc"]} == {99}
    assert {str(t) for t in result["type_name"]} == {"G", "*"}


def test_get_new_redshift_records_defaults_null_e_cz(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "cz_table")
    layer_seed.register_records(storage, "cz_table", ["r1", "r2"])
    layer_seed.register_pgcs(storage, [10, 20])
    layer_seed.upsert_pgc(storage, {"r1": 10, "r2": 20})
    layer_seed.save_structured_data(
        storage,
        layer1.RedshiftCatalogObject.layer1_table(),
        layer1.RedshiftCatalogObject.layer1_keys(),
        ["r1", "r2"],
        [[1000.0, 10.0], [2000.0, None]],
        conflict_keys=layer1.RedshiftCatalogObject.layer1_primary_keys(),
    )

    result = repo.get_new_redshift_records(datetime.datetime.fromtimestamp(0, tz=datetime.UTC), limit=10, offset=0)

    assert len(result) == 2
    by_pgc = {
        int(pgc): (float(cz.to_value(u.Unit("km/s"))), float(e_cz.to_value(u.Unit("km/s"))))
        for pgc, cz, e_cz in zip(result["pgc"], result["cz"], result["e_cz"], strict=True)
    }
    assert by_pgc == {10: (1000.0, 10.0), 20: (2000.0, 100.0)}


def test_save_structured_data_logs_pgc_change(
    repo: repository.Repository,
    storage: postgres.PgStorage,
    pg_storage: PostgresTestStorage,
) -> None:
    _insert_nature_data(storage, "t_bump", ["rec1"], {"rec1": 5001}, [["G"]])
    old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    pg_storage.storage.exec("UPDATE common.pgc_changes SET changed_at = %s", params=[old_dt])

    layer_seed.save_structured_data(
        storage,
        layer1.NatureCatalogObject.layer1_table(),
        ["type_name"],
        ["rec1"],
        [["QSO"]],
    )

    rows = pg_storage.storage.query("SELECT pgc FROM common.pgc_changes WHERE changed_at > %s", params=[old_dt])
    assert [row["pgc"] for row in rows] == [5001]

    after_old = repo.get_new_nature_records(datetime.datetime(2000, 1, 2, tzinfo=datetime.UTC), 10, 0)
    assert len(after_old) == 1
    assert int(after_old["pgc"][0]) == 5001

    future = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
    assert len(repo.get_new_nature_records(future, 10, 0)) == 0


def _seed_nature_pgcs(storage: postgres.PgStorage, table_name: str, pgcs: list[int]) -> None:
    record_ids = [f"{table_name}-{pgc}" for pgc in pgcs]
    _insert_nature_data(storage, table_name, record_ids, dict(zip(record_ids, pgcs, strict=True)), [["G"]] * len(pgcs))
    storage.exec("DELETE FROM common.pgc_changes")


def _log_change(storage: postgres.PgStorage, pgc: int, changed_at: datetime.datetime) -> None:
    storage.exec("INSERT INTO common.pgc_changes (pgc, changed_at) VALUES (%s, %s)", params=[pgc, changed_at])


def test_touch_pgcs_appends_deduplicated_rows(storage: postgres.PgStorage) -> None:
    layer0.touch_pgcs(storage, [3, 1, 3])
    layer0.touch_pgcs(storage, [1])
    layer0.touch_pgcs(storage, [])

    rows = storage.query("SELECT pgc FROM common.pgc_changes ORDER BY pgc")
    assert [row["pgc"] for row in rows] == [1, 1, 3]


def test_consumer_queries_return_each_changed_pgc_once(
    storage: postgres.PgStorage,
    repo: repository.Repository,
) -> None:
    _seed_nature_pgcs(storage, "t_consumer", [10, 20, 30, 40])
    old = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    new = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    watermark = datetime.datetime(2010, 1, 1, tzinfo=datetime.UTC)
    for pgc in (10, 20, 30):
        _log_change(storage, pgc, new)
        _log_change(storage, pgc, new + datetime.timedelta(hours=1))
    _log_change(storage, 40, old)
    _log_change(storage, 99, new)

    records = repo.get_new_nature_records(watermark, 2, 0)
    assert [int(pgc) for pgc in records["pgc"]] == [10, 20]
    records = repo.get_new_nature_records(watermark, 2, 20)
    assert [int(pgc) for pgc in records["pgc"]] == [30]

    modified = repo.get_modified_object_pgcs(watermark, 10, 0)
    assert [int(pgc) for pgc in modified["pgc"]] == [10, 20, 30]


def test_get_modified_object_pgcs_dedupes_and_paginates(
    storage: postgres.PgStorage,
    repo: repository.Repository,
) -> None:
    _seed_nature_pgcs(storage, "t_modified", [10, 20, 30])
    new = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    for pgc in (10, 20, 30):
        _log_change(storage, pgc, new)
        _log_change(storage, pgc, new)
    watermark = datetime.datetime(2010, 1, 1, tzinfo=datetime.UTC)

    assert [int(p) for p in repo.get_modified_object_pgcs(watermark, 2, 0)["pgc"]] == [10, 20]
    assert [int(p) for p in repo.get_modified_object_pgcs(watermark, 2, 20)["pgc"]] == [30]
    later = datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC)
    assert len(repo.get_modified_object_pgcs(later, 10, 0)) == 0


def test_prune_pgc_changes_keeps_rows_newer_than_oldest_watermark(
    storage: postgres.PgStorage,
    repo: repository.Repository,
) -> None:
    storage.exec("DELETE FROM common.pgc_changes")
    for catalog in layer2.Catalog:
        repo.update_last_update_time(datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC), catalog)
    repo.update_last_update_time(datetime.datetime(2015, 1, 1, tzinfo=datetime.UTC), layer2.Catalog.ICRS)
    _log_change(storage, 1, datetime.datetime(2014, 1, 1, tzinfo=datetime.UTC))
    _log_change(storage, 2, datetime.datetime(2016, 1, 1, tzinfo=datetime.UTC))
    _log_change(storage, 3, datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC))

    repo.prune_pgc_changes()

    rows = storage.query("SELECT pgc FROM common.pgc_changes ORDER BY pgc")
    assert [row["pgc"] for row in rows] == [2, 3]


def test_get_database_time_is_close_to_now(repo: repository.Repository) -> None:
    got = repo.get_database_time()
    now = datetime.datetime.now(tz=datetime.UTC)
    assert abs((got - now).total_seconds()) < 60


def test_migration_backfill_logs_pgcs_modified_after_oldest_watermark(
    storage: postgres.PgStorage,
    repo: repository.Repository,
) -> None:
    layer_seed.register_pgcs(storage, [1, 2])
    storage.exec("DELETE FROM common.pgc_changes")
    for catalog in layer2.Catalog:
        repo.update_last_update_time(datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC), catalog)
    storage.exec(
        "UPDATE common.pgc SET modification_time = %s WHERE id = 1",
        params=[datetime.datetime(2019, 1, 1, tzinfo=datetime.UTC)],
    )
    storage.exec(
        "UPDATE common.pgc SET modification_time = %s WHERE id = 2",
        params=[datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC)],
    )

    migration = pathlib.Path("postgres/migrations/V081__pgc_change_log.sql").read_text()
    storage.exec(migration[migration.index("INSERT INTO") :])

    rows = storage.query("SELECT pgc, changed_at FROM common.pgc_changes WHERE pgc IN (1, 2)")
    assert [(row["pgc"], row["changed_at"].replace(tzinfo=datetime.UTC)) for row in rows] == [
        (2, datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC))
    ]
