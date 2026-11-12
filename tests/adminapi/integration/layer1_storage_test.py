import math

import psycopg
import pytest

from app.catalogs import layer1
from app.lib.storage import postgres
from app.lib.storage.postgres.transactional import TransactionalPGRepository
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")

NATURE = layer1.NatureCatalogObject.layer1_table()
CZ = layer1.RedshiftCatalogObject.layer1_table()
DESIGNATION = layer1.DesignationCatalogObject.layer1_table()


@pytest.fixture(scope="module")
def storage(pg_storage: PostgresTestStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


def _register(storage: postgres.PgStorage, table_name: str, record_ids: list[str]) -> None:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, record_ids)


def test_save_structured_data_behaviors(storage: postgres.PgStorage) -> None:
    repo = TransactionalPGRepository(storage)
    _register(storage, "t_dup", ["r1", "r2"])
    layer1.save_structured_data(storage, NATURE, ["type_name"], ["r1", "r2", "r1"], [["G"], ["QSO"], ["QSO"]])
    assert storage.query("SELECT record_id, type_name FROM nature.data ORDER BY record_id") == [
        {"record_id": "r1", "type_name": "QSO"},
        {"record_id": "r2", "type_name": "QSO"},
    ]

    _register(storage, "t_upd", ["r1"])
    layer1.save_structured_data(storage, NATURE, ["type_name"], ["r1"], [["G"]])
    layer1.save_structured_data(storage, NATURE, ["type_name"], ["r1"], [["QSO"]])
    assert storage.query("SELECT type_name FROM nature.data WHERE record_id = 'r1'") == [{"type_name": "QSO"}]

    keys = layer1.DesignationCatalogObject.layer1_primary_keys()
    _register(storage, "t_nothing", ["r1"])
    for _ in range(2):
        layer1.save_structured_data(
            storage, DESIGNATION, ["design"], ["r1", "r1"], [["NGC 1"], ["NGC 1"]], conflict_keys=keys
        )
    assert storage.query("SELECT design FROM designation.data WHERE record_id = 'r1'") == [{"design": "NGC 1"}]

    before = len(storage.query("SELECT 1 FROM nature.data"))
    layer1.save_structured_data(storage, NATURE, ["type_name"], [], [])
    assert len(storage.query("SELECT 1 FROM nature.data")) == before

    _register(storage, "t_enum", ["r1", "r2", "r3"])
    layer1.save_structured_data(
        storage,
        CZ,
        ["cz", "e_cz", "method"],
        ["r1", "r2", "r3"],
        [[1000.0, None, "emission"], [2000.0, 5.0, "best"], [float("nan"), float("nan"), "xcorr"]],
        conflict_keys=["record_id", "method"],
    )
    rows = storage.query("SELECT record_id, cz, e_cz, method::text AS method FROM cz.data ORDER BY record_id")
    assert rows[0] == {"record_id": "r1", "cz": 1000.0, "e_cz": None, "method": "emission"}
    assert rows[1] == {"record_id": "r2", "cz": 2000.0, "e_cz": 5.0, "method": "best"}
    assert math.isnan(rows[2]["cz"]) and math.isnan(rows[2]["e_cz"]) and rows[2]["method"] == "xcorr"

    cz_keys = layer1.RedshiftCatalogObject.layer1_primary_keys()
    _register(storage, "t_default_key", ["d1"])
    layer1.save_structured_data(
        storage, CZ, ["cz", "e_cz"], ["d1", "d1"], [[1.0, 1.0], [2.0, 2.0]], conflict_keys=cz_keys
    )
    layer1.save_structured_data(storage, CZ, ["cz", "e_cz"], ["d1"], [[3.0, 3.0]], conflict_keys=cz_keys)
    assert storage.query("SELECT cz, method::text AS method FROM cz.data WHERE record_id = 'd1'") == [
        {"cz": 3.0, "method": "unknown"}
    ]

    _register(storage, "t_tx", ["tx1", "tx2"])
    with repo.with_tx():
        layer1.save_structured_data(storage, NATURE, ["type_name"], ["tx1"], [["G"]])
        layer1.save_structured_data(storage, NATURE, ["type_name"], ["tx2"], [["QSO"]])
        layer1.save_structured_data(storage, CZ, ["cz", "e_cz"], ["tx1"], [[1.0, 1.0]], conflict_keys=cz_keys)
    assert len(storage.query("SELECT 1 FROM nature.data WHERE record_id IN ('tx1', 'tx2')")) == 2
    assert len(storage.query("SELECT 1 FROM cz.data WHERE record_id = 'tx1'")) == 1

    _register(storage, "t_fk", ["fk1"])
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        layer1.save_structured_data(storage, NATURE, ["type_name"], ["fk1"], [["NOT_A_TYPE"]])
    with pytest.raises(psycopg.errors.CheckViolation):
        layer1.save_structured_data(
            storage,
            layer1.ICRSCatalogObject.layer1_table(),
            layer1.ICRSCatalogObject.layer1_keys(),
            ["fk1"],
            [[400.0, 0.1, 1.0, 0.1]],
        )
    _register(storage, "t_repo_fk", ["fk2"])
    with pytest.raises(psycopg.errors.ForeignKeyViolation), repo.with_tx():
        layer1.save_structured_data(storage, NATURE, ["type_name"], ["fk2"], [["NOT_A_TYPE"]])
