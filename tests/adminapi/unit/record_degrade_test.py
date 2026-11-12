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
    records = Layer0TableRepository(storage).fetch_records(None, limit=25, row_offset=0)
    assert [record.id for record in records] == ["a", "b"]
    assert records[0].original_data == {}
    assert records[1].original_data == {"name": "ok"}


def test_layer1_getters_skip_null_required_fields() -> None:
    storage = mock.MagicMock()
    repo = Layer1Repository(storage, mock.MagicMock())

    storage.query.return_value = [
        {"record_id": "bad", "ra": None, "e_ra": 1, "dec": 2, "e_dec": 3},
        {"record_id": "ok", "ra": 1.0, "e_ra": 0.1, "dec": 2.0, "e_dec": 0.2},
    ]
    icrs = repo.get_icrs_records(["bad", "ok"])
    assert icrs[0] is None and icrs[1] is not None and icrs[1].ra == 1.0

    storage.query.return_value = [
        {"record_id": "bad", "cz": None, "e_cz": 1},
        {"record_id": "ok", "cz": 100.0, "e_cz": None},
    ]
    with mock.patch.object(repo, "get_column_units", return_value={"e_cz": "km/s"}):
        redshift = repo.get_redshift_records(["bad", "ok"])
    assert redshift[0] is None and redshift[1] is not None
    assert redshift[1].cz == 100.0 and redshift[1].e_cz == 100.0
