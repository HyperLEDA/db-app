import math

import psycopg
import pytest
import structlog

from app.catalogs import layer1
from app.lib.storage import postgres
from app.tasks import repository
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")

NATURE_TABLE = layer1.NatureCatalogObject.layer1_table()
CZ_TABLE = layer1.RedshiftCatalogObject.layer1_table()
DESIGNATION_TABLE = layer1.DesignationCatalogObject.layer1_table()


@pytest.fixture(scope="module")
def storage(pg_storage: PostgresTestStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


@pytest.fixture(scope="module")
def repo(storage: postgres.PgStorage) -> repository.Repository:
    return repository.Repository(storage, structlog.get_logger())


def _register(storage: postgres.PgStorage, table_name: str, record_ids: list[str]) -> None:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, record_ids)


def test_duplicate_keys_last_wins(storage: postgres.PgStorage) -> None:
    _register(storage, "t_dup", ["r1", "r2"])

    layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1", "r2", "r1"], [["G"], ["QSO"], ["QSO"]])

    result = storage.query("SELECT record_id, type_name FROM nature.data ORDER BY record_id")
    assert result == [{"record_id": "r1", "type_name": "QSO"}, {"record_id": "r2", "type_name": "QSO"}]


def test_upsert_overwrites_existing_row(storage: postgres.PgStorage) -> None:
    _register(storage, "t_upd", ["r1"])

    layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1"], [["G"]])
    layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1"], [["QSO"]])

    result = storage.query("SELECT type_name FROM nature.data WHERE record_id = 'r1'")
    assert result == [{"type_name": "QSO"}]


def test_do_nothing_when_all_columns_are_keys(storage: postgres.PgStorage) -> None:
    _register(storage, "t_nothing", ["r1"])
    keys = layer1.DesignationCatalogObject.layer1_primary_keys()

    for _ in range(2):
        layer1.save_structured_data(
            storage, DESIGNATION_TABLE, ["design"], ["r1", "r1"], [["NGC 1"], ["NGC 1"]], conflict_keys=keys
        )

    result = storage.query("SELECT design FROM designation.data WHERE record_id = 'r1'")
    assert result == [{"design": "NGC 1"}]


def test_enum_column_and_null_round_trip(storage: postgres.PgStorage) -> None:
    _register(storage, "t_enum", ["r1", "r2", "r3"])

    layer1.save_structured_data(
        storage,
        CZ_TABLE,
        ["cz", "e_cz", "method"],
        ["r1", "r2", "r3"],
        [[1000.0, None, "emission"], [2000.0, 5.0, "best"], [float("nan"), float("nan"), "xcorr"]],
        conflict_keys=["record_id", "method"],
    )

    result = storage.query("SELECT record_id, cz, e_cz, method::text AS method FROM cz.data ORDER BY record_id")
    assert result[0] == {"record_id": "r1", "cz": 1000.0, "e_cz": None, "method": "emission"}
    assert result[1] == {"record_id": "r2", "cz": 2000.0, "e_cz": 5.0, "method": "best"}
    assert math.isnan(result[2]["cz"])
    assert math.isnan(result[2]["e_cz"])
    assert result[2]["method"] == "xcorr"


def test_conflict_key_with_default_not_passed(storage: postgres.PgStorage) -> None:
    _register(storage, "t_default_key", ["r1"])
    keys = layer1.RedshiftCatalogObject.layer1_primary_keys()

    layer1.save_structured_data(
        storage, CZ_TABLE, ["cz", "e_cz"], ["r1", "r1"], [[1.0, 1.0], [2.0, 2.0]], conflict_keys=keys
    )
    layer1.save_structured_data(storage, CZ_TABLE, ["cz", "e_cz"], ["r1"], [[3.0, 3.0]], conflict_keys=keys)

    result = storage.query("SELECT cz, method::text AS method FROM cz.data WHERE record_id = 'r1'")
    assert result == [{"cz": 3.0, "method": "unknown"}]


def test_foreign_key_violation_is_raised(storage: postgres.PgStorage) -> None:
    _register(storage, "t_fk", ["r1"])

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1"], [["NOT_A_TYPE"]])


def test_check_violation_is_raised(storage: postgres.PgStorage) -> None:
    _register(storage, "t_check", ["r1"])

    with pytest.raises(psycopg.errors.CheckViolation):
        layer1.save_structured_data(
            storage,
            layer1.ICRSCatalogObject.layer1_table(),
            layer1.ICRSCatalogObject.layer1_keys(),
            ["r1"],
            [[400.0, 0.1, 1.0, 0.1]],
        )


def test_empty_input_is_noop(storage: postgres.PgStorage) -> None:
    layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], [], [])

    assert storage.query("SELECT 1 FROM nature.data") == []


def test_two_calls_in_one_transaction(repo: repository.Repository, storage: postgres.PgStorage) -> None:
    _register(storage, "t_tx", ["r1", "r2"])

    with repo.with_tx():
        layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1"], [["G"]])
        layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r2"], [["QSO"]])
        layer1.save_structured_data(
            storage,
            CZ_TABLE,
            ["cz", "e_cz"],
            ["r1"],
            [[1.0, 1.0]],
            conflict_keys=layer1.RedshiftCatalogObject.layer1_primary_keys(),
        )

    assert len(storage.query("SELECT 1 FROM nature.data")) == 2
    assert len(storage.query("SELECT 1 FROM cz.data")) == 1


def test_repository_converts_foreign_key_violation(repo: repository.Repository, storage: postgres.PgStorage) -> None:
    _register(storage, "t_repo_fk", ["r1"])

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with repo.with_tx():
            layer1.save_structured_data(storage, NATURE_TABLE, ["type_name"], ["r1"], [["NOT_A_TYPE"]])
