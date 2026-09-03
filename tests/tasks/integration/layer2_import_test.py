from collections.abc import Generator

import pytest
import structlog

from app import catalogs, tasks
from app.lib.storage import postgres
from app.tasks import layer2_import, repository
from tests.lib import assert_catalog_object_equal, layer_seed
from tests.lib.postgres import TestPostgresStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def storage(pg_storage: TestPostgresStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


@pytest.fixture(scope="module")
def repo(storage: postgres.PgStorage) -> repository.Repository:
    return repository.Repository(storage, structlog.get_logger())


@pytest.fixture(scope="module")
def layer2_import_task(pg_storage: TestPostgresStorage) -> Generator[layer2_import.Layer2ImportTask]:
    task = layer2_import.Layer2ImportTask(structlog.get_logger())
    task.prepare(tasks.Config(storage=pg_storage.config))
    yield task
    task.cleanup()


def _get_table(storage: postgres.PgStorage, table_name: str) -> int:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    return layer_seed.create_table(storage, table_name, bib_id)


def _designation(storage: postgres.PgStorage, pgc: int) -> catalogs.DesignationCatalogObject | None:
    rows = storage.query(
        "SELECT design FROM layer2.designation WHERE pgc = %s",
        params=[pgc],
    )
    if not rows:
        return None
    return catalogs.DesignationCatalogObject(design=rows[0]["design"])


def _icrs(storage: postgres.PgStorage, pgc: int) -> catalogs.ICRSCatalogObject | None:
    rows = storage.query(
        "SELECT ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = %s",
        params=[pgc],
    )
    if not rows:
        return None
    row = rows[0]
    return catalogs.ICRSCatalogObject(ra=row["ra"], e_ra=row["e_ra"], dec=row["dec"], e_dec=row["e_dec"])


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
        conflict_keys=catalogs.DesignationCatalogObject.layer1_primary_keys(),
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
    assert_catalog_object_equal(icrs, catalogs.ICRSCatalogObject(ra=12, e_ra=0.2, dec=13, e_dec=0.2))
    assert_catalog_object_equal(designation, catalogs.DesignationCatalogObject("test1"))


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

    last_update_dt = repo.get_last_update_time(catalogs.RawCatalog.DESIGNATION)

    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["125", "126"],
        [["test3"], ["test3"]],
        conflict_keys=catalogs.DesignationCatalogObject.layer1_primary_keys(),
    )

    layer2_import_task.run()

    new_last_update_dt = repo.get_last_update_time(catalogs.RawCatalog.DESIGNATION)
    assert new_last_update_dt > last_update_dt

    designation = _designation(storage, 1234)
    assert designation is not None
    assert_catalog_object_equal(designation, catalogs.DesignationCatalogObject("test3"))


def test_layer1_only_update_recalculates_layer2(
    storage: postgres.PgStorage,
    repo: repository.Repository,
    layer2_import_task: layer2_import.Layer2ImportTask,
) -> None:
    _import_two_catalogs(storage, layer2_import_task)

    last_update_dt = repo.get_last_update_time(catalogs.RawCatalog.ICRS)

    layer_seed.save_structured_data(
        storage,
        "icrs.data",
        ["ra", "e_ra", "dec", "e_dec"],
        ["123"],
        [[22.0, 0.2, 23.0, 0.2]],
    )

    layer2_import_task.run()

    new_last_update_dt = repo.get_last_update_time(catalogs.RawCatalog.ICRS)
    assert new_last_update_dt > last_update_dt

    icrs = _icrs(storage, 1234)
    assert icrs is not None
    assert_catalog_object_equal(icrs, catalogs.ICRSCatalogObject(ra=22.0, e_ra=0.2, dec=23.0, e_dec=0.2))
