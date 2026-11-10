from unittest import mock

from app.adminapi.repository.layer0.tables import Layer0TableRepository
from app.adminapi.repository.layer1 import Layer1Repository


def test_fetch_records_keeps_rows_when_raw_table_query_fails() -> None:
    storage = mock.MagicMock()
    storage.query.side_effect = [
        [
            {"id": "a", "pgc": None, "table_name": "gone"},
            {"id": "b", "pgc": None, "table_name": "kept"},
        ],
        RuntimeError("missing relation"),
        [{"hyperleda_internal_id": "b", "name": "ok"}],
    ]
    repo = Layer0TableRepository(storage)

    records = repo.fetch_records(None, limit=25, row_offset=0)

    assert [record.id for record in records] == ["a", "b"]
    assert records[0].original_data == {}
    assert records[1].original_data == {"name": "ok"}


def test_get_icrs_records_skips_null_coordinate() -> None:
    storage = mock.MagicMock()
    storage.query.return_value = [
        {"record_id": "bad", "ra": None, "e_ra": 1, "dec": 2, "e_dec": 3},
        {"record_id": "ok", "ra": 1.0, "e_ra": 0.1, "dec": 2.0, "e_dec": 0.2},
    ]
    repo = Layer1Repository(storage, mock.MagicMock())

    result = repo.get_icrs_records(["bad", "ok"])

    assert result[0] is None
    assert result[1] is not None
    assert result[1].ra == 1.0


def test_get_redshift_records_skips_null_cz() -> None:
    storage = mock.MagicMock()
    storage.query.return_value = [
        {"record_id": "bad", "cz": None, "e_cz": 1},
        {"record_id": "ok", "cz": 100.0, "e_cz": None},
    ]
    repo = Layer1Repository(storage, mock.MagicMock())

    with mock.patch.object(repo, "get_column_units", return_value={"e_cz": "km/s"}):
        result = repo.get_redshift_records(["bad", "ok"])

    assert result[0] is None
    assert result[1] is not None
    assert result[1].cz == 100.0
    assert result[1].e_cz == 100.0
