import datetime

import pytest
import structlog

from app import catalogs
from app.adminapi import model, repository
from app.lib.storage import enums, postgres
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


def _get_table(repo: repository.Repository, table_name: str) -> int:
    bib_id = repo.create_bibliography("123456", 2000, ["test"], "test")
    table_resp = repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(schema=repository.RAWDATA_SCHEMA, name=table_name),
            bib_id,
        )
    )
    return table_resp.table_id


def _insert_nature_data(
    repo: repository.Repository,
    table_name: str,
    record_ids: list[str],
    pgcs: dict[str, int],
    rows: list[list[str]],
) -> None:
    _get_table(repo, table_name)
    repo.register_records(table_name, record_ids)
    repo.register_pgcs(list(pgcs.values()))
    repo.upsert_pgc(pgcs)
    columns = ["type_name"]
    repo.save_structured_data(
        catalogs.NatureCatalogObject.layer1_table(),
        columns,
        record_ids,
        rows,
    )


def test_icrs(repo: repository.Repository, pg_storage: PostgresTestStorage) -> None:
    bib_id = repo.create_bibliography("123456", 2000, ["test"], "test")
    _ = repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test_table",
                columns={
                    "ra": postgres.ColumnInfo("ra", "float", ucd="pos.eq.ra", unit="hour"),
                    "dec": postgres.ColumnInfo("dec", "float", ucd="pos.eq.dec", unit="hour"),
                    "e_ra": postgres.ColumnInfo("e_ra", "float", ucd="stat.error", unit="hour"),
                    "e_dec": postgres.ColumnInfo("e_dec", "float", ucd="stat.error", unit="hour"),
                },
            ),
            bib_id,
            enums.DataType.REGULAR,
        )
    )
    repo.register_records("test_table", ["111", "112"])
    columns = catalogs.ICRSCatalogObject.layer1_keys()
    repo.save_structured_data(
        catalogs.ICRSCatalogObject.layer1_table(),
        columns,
        ["111", "112"],
        [[12.1, 0.1, 1, 0.3], [11.1, 0.2, 2, 0.4]],
    )

    result = pg_storage.storage.query("SELECT ra FROM icrs.data ORDER BY ra")
    assert result == [{"ra": 11.1}, {"ra": 12.1}]


def test_designation_multiple_names_per_record(repo: repository.Repository, pg_storage: PostgresTestStorage) -> None:
    _get_table(repo, "desig_table")
    repo.register_records("desig_table", ["r1"])
    repo.save_structured_data(
        catalogs.DesignationCatalogObject.layer1_table(),
        catalogs.DesignationCatalogObject.layer1_keys(),
        ["r1", "r1"],
        [["NGC 224"], ["M 31"]],
        conflict_keys=catalogs.DesignationCatalogObject.layer1_primary_keys(),
    )

    result = pg_storage.storage.query(
        "SELECT design FROM designation.data WHERE record_id = %s ORDER BY design",
        params=["r1"],
    )

    assert result == [{"design": "M 31"}, {"design": "NGC 224"}]


def test_get_redshift_records_defaults_null_e_cz(repo: repository.Repository) -> None:
    _get_table(repo, "cz_table")
    repo.register_records("cz_table", ["r1", "r2"])
    repo.save_structured_data(
        catalogs.RedshiftCatalogObject.layer1_table(),
        catalogs.RedshiftCatalogObject.layer1_keys(),
        ["r1", "r2"],
        [[1000.0, 10.0], [2000.0, None]],
        conflict_keys=catalogs.RedshiftCatalogObject.layer1_primary_keys(),
    )

    result = repo.get_redshift_records(["r1", "r2", "missing"])

    assert len(result) == 3
    assert result[0] is not None
    assert result[1] is not None
    assert result[2] is None
    assert result[0].cz == 1000.0
    assert result[0].e_cz == 10.0
    assert result[1].cz == 2000.0
    assert result[1].e_cz == 100.0


def test_save_structured_data_bumps_pgc_modification_time(
    repo: repository.Repository,
    pg_storage: PostgresTestStorage,
) -> None:
    _insert_nature_data(repo, "t_bump", ["rec1"], {"rec1": 5001}, [["G"]])
    old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    pg_storage.storage.exec(
        "UPDATE common.pgc SET modification_time = %s WHERE id = %s",
        params=[old_dt, 5001],
    )

    repo.save_structured_data(
        catalogs.NatureCatalogObject.layer1_table(),
        ["type_name"],
        ["rec1"],
        [["QSO"]],
    )

    row = pg_storage.storage.query_one(
        "SELECT modification_time FROM common.pgc WHERE id = %s",
        params=[5001],
    )
    assert row["modification_time"].replace(tzinfo=datetime.UTC) > old_dt
