import numpy as np
import pandas as pd
import pytest
import structlog
from astropy import units as u

from app.adminapi import model, repository
from app.lib.storage import postgres
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


def test_write_and_fetch_table(repo: repository.Repository) -> None:
    bib_id = repo.create_bibliography("123456", 2000, ["test"], "test")
    table_meta = model.Layer0TableMeta(
        postgres.TableInfo(
            schema=repository.RAWDATA_SCHEMA,
            name="test_table",
            columns={
                "ra": postgres.ColumnInfo("ra", "float", ucd="pos.eq.ra", unit="hour"),
                "dec": postgres.ColumnInfo("dec", "float", ucd="pos.eq.dec", unit="hour"),
            },
        ),
        bib_id,
    )

    _ = repo.create_table(table_meta)
    test_data = pd.DataFrame({"ra": [12.1, 11.1], "dec": [1.0, 2.0]})
    raw_data = model.Layer0RawData(table_meta.table_info.name, test_data)

    repo.insert_raw_data(raw_data)

    fetched_data = repo.fetch_table(table_meta.table_info.name)

    assert len(fetched_data) == 2
    assert list(fetched_data.columns) == ["ra", "dec"]

    np.testing.assert_array_equal(fetched_data["ra"], test_data["ra"])
    assert fetched_data["ra"].unit == u.Unit("hour")
    np.testing.assert_array_equal(fetched_data["dec"], test_data["dec"])
