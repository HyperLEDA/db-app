import datetime
from collections.abc import Generator
from unittest import mock

import pytest
import structlog

from app import tasks
from app.catalogs import layer1, layer2
from app.lib.storage import postgres
from app.tasks import layer2_common, layer2_import, repository
from tests.lib import assert_catalog_object_equal, layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def storage(pg_storage: PostgresTestStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


@pytest.fixture(scope="module")
def repo(storage: postgres.PgStorage) -> repository.Repository:
    return repository.Repository(storage, structlog.get_logger())


@pytest.fixture(scope="module")
def layer2_import_task(pg_storage: PostgresTestStorage) -> Generator[layer2_import.Layer2ImportTask]:
    task = layer2_import.Layer2ImportTask(structlog.get_logger())
    task.prepare(tasks.Config(storage=pg_storage.config))
    task.fieldapi_client = _ConstantEbv()
    yield task
    task.cleanup()


class _ConstantEbv:
    def sample_sfd_ebv(self, coordinates: list[object]) -> list[float]:
        return [0.01 for _ in coordinates]


def _get_table(storage: postgres.PgStorage, table_name: str) -> int:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    return layer_seed.create_table(storage, table_name, bib_id)


def _designation(storage: postgres.PgStorage, pgc: int) -> layer2.DesignationCatalogObject | None:
    rows = storage.query(
        "SELECT design FROM layer2.designation WHERE pgc = %s",
        params=[pgc],
    )
    if not rows:
        return None
    return layer2.DesignationCatalogObject(design=rows[0]["design"])


def _icrs(storage: postgres.PgStorage, pgc: int) -> layer2.ICRSCatalogObject | None:
    rows = storage.query(
        "SELECT ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = %s",
        params=[pgc],
    )
    if not rows:
        return None
    row = rows[0]
    return layer2.ICRSCatalogObject(ra=row["ra"], e_ra=row["e_ra"], dec=row["dec"], e_dec=row["e_dec"])


def _import_two_catalogs(
    storage: postgres.PgStorage,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    _ = _get_table(storage, "test_import_two_catalogs")
    layer_seed.register_records(
        storage,
        "test_import_two_catalogs",
        ["123", "124"],
    )
    layer_seed.register_pgcs(storage, [1234, 1245])
    layer_seed.upsert_pgc(storage, {"123": 1234, "124": 1245})
    layer_seed.save_structured_data(
        storage,
        "icrs.data",
        ["ra", "e_ra", "dec", "e_dec"],
        ["123", "124"],
        [[12, 0.2, 13, 0.2], [14, 0.2, 15, 0.2]],
    )
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["123", "124"],
        [["test1"], ["test2"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )

    layer2_import_task.run()


def test_import_two_catalogs(
    storage: postgres.PgStorage,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    _import_two_catalogs(storage, layer2_import_task)

    icrs = _icrs(storage, 1234)
    designation = _designation(storage, 1234)
    assert icrs is not None
    assert designation is not None
    assert_catalog_object_equal(icrs, layer2.ICRSCatalogObject(ra=12, e_ra=0.2, dec=13, e_dec=0.2))
    assert_catalog_object_equal(designation, layer2.DesignationCatalogObject("test1"))


def test_updated_objects(
    storage: postgres.PgStorage,
    repo: repository.Repository,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    _import_two_catalogs(storage, layer2_import_task)
    _ = _get_table(storage, "test_updated_objects")
    layer_seed.register_records(
        storage,
        "test_updated_objects",
        ["125", "126"],
    )
    layer_seed.upsert_pgc(storage, {"125": 1234, "126": 1234})

    last_update_dt = repo.get_last_update_time(layer2.Catalog.DESIGNATION)

    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["125", "126"],
        [["test3"], ["test3"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )

    layer2_import_task.run()

    new_last_update_dt = repo.get_last_update_time(layer2.Catalog.DESIGNATION)
    assert new_last_update_dt > last_update_dt

    designation = _designation(storage, 1234)
    assert designation is not None
    assert_catalog_object_equal(designation, layer2.DesignationCatalogObject("test3"))


def test_layer1_only_update_recalculates_layer2(
    storage: postgres.PgStorage,
    repo: repository.Repository,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    _import_two_catalogs(storage, layer2_import_task)

    last_update_dt = repo.get_last_update_time(layer2.Catalog.ICRS)

    layer_seed.save_structured_data(
        storage,
        "icrs.data",
        ["ra", "e_ra", "dec", "e_dec"],
        ["123"],
        [[22.0, 0.2, 23.0, 0.2]],
    )

    layer2_import_task.run()

    new_last_update_dt = repo.get_last_update_time(layer2.Catalog.ICRS)
    assert new_last_update_dt > last_update_dt

    icrs = _icrs(storage, 1234)
    assert icrs is not None
    assert_catalog_object_equal(icrs, layer2.ICRSCatalogObject(ra=22.0, e_ra=0.2, dec=23.0, e_dec=0.2))


def test_watermark_dry_run_and_late_change_log(
    storage: postgres.PgStorage,
    repo: repository.Repository,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    dry = layer2_import.Layer2ImportTask(structlog.get_logger(), dry_run=True, silent=True)
    dry.pg_storage = storage
    dry.repository = repo
    dry.fieldapi_client = _ConstantEbv()
    before = repo.get_last_update_time(layer2.Catalog.ICRS)
    storage.exec("INSERT INTO common.pgc_changes (pgc, changed_at) VALUES (1, TIMESTAMP '1971-01-01')")
    dry.run()
    assert repo.get_last_update_time(layer2.Catalog.ICRS) == before
    assert storage.query_one("SELECT count(*) AS n FROM common.pgc_changes WHERE pgc = 1")["n"] == 1

    run_start = datetime.datetime(2030, 5, 1, 12, 0, 0, tzinfo=datetime.UTC)
    with mock.patch.object(layer2_import_task.repository, "get_database_time", return_value=run_start):
        layer2_import_task.run()
    expected = (run_start - layer2_common.WATERMARK_SAFETY_MARGIN).replace(tzinfo=None)
    for catalog in layer2_import.DEFAULT_CATALOGS:
        assert repo.get_last_update_time(layer2.Catalog(catalog)) == expected

    watermark = repo.get_last_update_time(layer2.Catalog.DESIGNATION)
    _ = _get_table(storage, "test_race")
    layer_seed.register_records(storage, "test_race", ["race1"])
    layer_seed.register_pgcs(storage, [7777])
    layer_seed.upsert_pgc(storage, {"race1": 7777})
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["race1"],
        [["race"]],
        conflict_keys=layer1.DesignationCatalogObject.layer1_primary_keys(),
    )
    storage.exec(
        "UPDATE common.pgc_changes SET changed_at = %s WHERE pgc = 7777",
        params=[watermark + datetime.timedelta(minutes=1)],
    )
    layer2_import_task.run()
    designation = _designation(storage, 7777)
    assert designation is not None
    assert_catalog_object_equal(designation, layer2.DesignationCatalogObject("race"))
