from contextlib import contextmanager

import pytest
from astropy import units

from app.adminapi import clients, domain, model, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.adminapi.domain.table_upload import domain_descriptions_to_data, ensure_source_id
from app.lib import mock
from app.lib.storage import enums, mapping, postgres
from app.lib.web import errors
from app.specs import adminapi
from tests import lib

_INTERNAL_ID_COLUMN = postgres.ColumnInfo(
    name=repository.INTERNAL_ID_COLUMN_NAME,
    data_type=mapping.TYPE_TEXT,
    not_null=True,
)

_CREATE_TABLE_COLUMNS = [
    adminapi.ColumnDescription(name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"),
    adminapi.ColumnDescription(name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"),
    adminapi.ColumnDescription(name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"),
]


@contextmanager
def _null_context():
    yield


@pytest.fixture
def upload_manager() -> tuple[mock.MagicMock, domain.TableUploadManager]:
    repo = mock.MagicMock()
    repo.with_tx = mock.MagicMock(return_value=_null_context())
    manager = domain.TableUploadManager(
        repo,
        clients=clients.get_mock_clients(),
        table_stats_cache=get_mock_table_stats_cache(),
    )
    return repo, manager


@pytest.fixture
def get_records_manager() -> tuple[mock.MagicMock, domain.TableUploadManager]:
    repo = mock.MagicMock()
    repo.get_table_metadata.return_value = postgres.TableInfo(
        schema="",
        name="",
        description=None,
        columns={},
        primary_keys=set(),
    )
    repo.get_designation_records.side_effect = lambda record_ids: [None] * len(record_ids)
    repo.get_icrs_records.side_effect = lambda record_ids: [None] * len(record_ids)
    repo.get_redshift_records.side_effect = lambda record_ids: [None] * len(record_ids)
    repo.get_nature_records.side_effect = lambda record_ids: [None] * len(record_ids)
    repo.with_tx = mock.MagicMock(return_value=_null_context())
    repo.get_nature_object_types.return_value = []
    manager = domain.TableUploadManager(
        repo,
        clients=clients.get_mock_clients(),
        table_stats_cache=get_mock_table_stats_cache(),
    )
    return repo, manager


def test_add_data(upload_manager: tuple[mock.MagicMock, domain.TableUploadManager]) -> None:
    repo, manager = upload_manager
    request = adminapi.AddDataRequest(
        table_name="test_table",
        data=[
            {
                "test": "row",
                "number": 41,
            },
            {
                "test": "row2",
                "number": 43,
            },
        ],
    )

    _ = manager.add_data(request)

    call_args = repo.insert_raw_data.call_args

    assert list(call_args.args[0].data["test"]) == ["row", "row2"]
    assert list(call_args.args[0].data["number"]) == [41, 43]
    assert list(call_args.args[0].data["hyperleda_internal_id"]) == [
        "1b4bbb6e-27d8-f7b8-2a5e-3a37b1c3248e",
        "a62b5fd9-9b6a-964c-406d-3fa4fc3471d7",
    ]


def test_add_data_identical_rows(upload_manager: tuple[mock.MagicMock, domain.TableUploadManager]) -> None:
    repo, manager = upload_manager
    request = adminapi.AddDataRequest(
        table_name="test_table",
        data=[
            {
                "test": "row",
                "number": 41,
            },
            {
                "test": "row",
                "number": 41,
            },
        ],
    )

    _ = manager.add_data(request)

    call_args = repo.insert_raw_data.call_args

    assert list(call_args.args[0].data["test"]) == ["row"]
    assert list(call_args.args[0].data["number"]) == [41]


@pytest.mark.parametrize(
    "table_already_existed,expected_created,err_substr",
    [
        (False, True, None),
        (True, False, None),
    ],
    ids=["create new table", "create already existing table"],
)
def test_create_table(
    upload_manager: tuple[mock.MagicMock, domain.TableUploadManager],
    table_already_existed: bool,
    expected_created: bool,
    err_substr: str | None,
) -> None:
    repo, manager = upload_manager
    request = adminapi.CreateTableRequest(
        table_name="test",
        columns=_CREATE_TABLE_COLUMNS,
        bibcode="totally real bibcode",
        datatype=enums.DataType.REGULAR,
        description="",
    )
    lib.returns(repo.create_bibliography, 41)
    lib.returns(repo.create_table, model.Layer0CreationResponse(51, not table_already_existed))

    if err_substr is not None:
        with pytest.raises(errors.RuleValidationError) as err:
            manager.create_table(request)

        assert err_substr in err.value.message()
    else:
        resp, created = manager.create_table(request)
        assert resp.id == 51
        assert created == expected_created


@pytest.mark.parametrize(
    "code,ads_query_needed",
    [
        ("1982euse.book.....L", True),
        ("1975ApJS...45..113M", True),
        ("2011A&A...534A..31G", True),
        ("2011A&A.....31G", False),
        ("some_custom_code", False),
    ],
)
def test_ensure_source_id(
    upload_manager: tuple[mock.MagicMock, domain.TableUploadManager],
    code: str,
    ads_query_needed: bool,
) -> None:
    repo, manager = upload_manager
    lib.returns(repo.create_bibliography, 41)
    lib.returns(repo.get_source_entry, mock.MagicMock(id=42))
    lib.returns(
        manager.clients.ads.query_simple,
        [
            {
                "title": ["Some Title"],
                "author": ["Author1", "Author2"],
                "pubdate": "2011-01-00",
            }
        ],
    )

    result = ensure_source_id(repo, manager.clients.ads, code)
    if ads_query_needed:
        assert result == 41
    else:
        assert result == 42


def test_ads_not_found(upload_manager: tuple[mock.MagicMock, domain.TableUploadManager]) -> None:
    repo, manager = upload_manager
    lib.raises(manager.clients.ads.query_simple, RuntimeError("Not found"))

    with pytest.raises(errors.RuleValidationError):
        _ = ensure_source_id(repo, manager.clients.ads, "2000A&A...534A..31G")


def test_internal_comms_not_found(upload_manager: tuple[mock.MagicMock, domain.TableUploadManager]) -> None:
    repo, _manager = upload_manager
    lib.raises(repo.get_source_entry, RuntimeError("Not found"))
    ads_client = mock.MagicMock()

    with pytest.raises(errors.RuleValidationError):
        _ = ensure_source_id(repo, ads_client, "some_internal_code")


@pytest.mark.parametrize(
    "input_columns,expected,err_substr",
    [
        (
            [
                adminapi.ColumnDescription(
                    name="name",
                    data_type=adminapi.DatatypeEnum["str"],
                    ucd="phys.veloc.orbital",
                    unit="m / s",
                    description="description",
                )
            ],
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test",
                columns={
                    repository.INTERNAL_ID_COLUMN_NAME: _INTERNAL_ID_COLUMN,
                    "name": postgres.ColumnInfo(
                        "name",
                        "text",
                        ucd="phys.veloc.orbital",
                        unit=units.Unit("m / s").to_string(),
                        description="description",
                    ),
                },
                primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
            ),
            None,
        ),
        (
            [adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["str"])],
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test",
                columns={
                    repository.INTERNAL_ID_COLUMN_NAME: _INTERNAL_ID_COLUMN,
                    "name": postgres.ColumnInfo("name", "text"),
                },
                primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
            ),
            None,
        ),
        (
            [adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["str"], unit="m     /       s")],
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test",
                columns={
                    repository.INTERNAL_ID_COLUMN_NAME: _INTERNAL_ID_COLUMN,
                    "name": postgres.ColumnInfo("name", "text", unit=units.Unit("m / s").to_string()),
                },
                primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
            ),
            None,
        ),
        (
            [
                adminapi.ColumnDescription(
                    name="name",
                    data_type=adminapi.DatatypeEnum["str"],
                    unit="not_a_unit",
                    description="some description",
                )
            ],
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test",
                columns={
                    repository.INTERNAL_ID_COLUMN_NAME: _INTERNAL_ID_COLUMN,
                    "name": postgres.ColumnInfo("name", "text", description="some description (unit not_a_unit)"),
                },
                primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
            ),
            None,
        ),
        (
            [
                adminapi.ColumnDescription(
                    name="name",
                    data_type=adminapi.DatatypeEnum["str"],
                    unit="not_a_unit",
                )
            ],
            postgres.TableInfo(
                schema=repository.RAWDATA_SCHEMA,
                name="test",
                columns={
                    repository.INTERNAL_ID_COLUMN_NAME: _INTERNAL_ID_COLUMN,
                    "name": postgres.ColumnInfo("name", "text", description="(unit not_a_unit)"),
                },
                primary_keys={repository.INTERNAL_ID_COLUMN_NAME},
            ),
            None,
        ),
    ],
    ids=[
        "simple column",
        "unit is None",
        "unit has extra spaces",
        "invalid unit is ignored and appended to description",
        "invalid unit with no description",
    ],
)
def test_mapping(
    input_columns: list[adminapi.ColumnDescription],
    expected: postgres.TableInfo | None,
    err_substr: str | None,
) -> None:
    if err_substr:
        with pytest.raises(errors.RuleValidationError) as err:
            domain_descriptions_to_data("test", input_columns)

        assert err_substr in err.value.message()
    else:
        assert domain_descriptions_to_data("test", input_columns) == expected


def test_get_records_returns_records_with_pgc(
    get_records_manager: tuple[mock.MagicMock, domain.TableUploadManager],
) -> None:
    repo, manager = get_records_manager
    repo.fetch_records.return_value = [
        model.TableRecord(
            id="rec1", original_data={"name": "A"}, pgc=1001, triage_status="resolved", crossmatch_candidates=[1001]
        ),
        model.TableRecord(
            id="rec2",
            original_data={"name": "B"},
            pgc=1002,
            triage_status="pending",
            crossmatch_candidates=[],
        ),
    ]

    request = adminapi.GetRecordsRequest(table_name="t", page=0, page_size=25)
    response = manager.get_records(request)

    assert len(response.records) == 2
    assert response.records[0].id == "rec1"
    assert response.records[0].original_data == {"name": "A"}
    assert response.records[0].pgc == 1001
    assert response.records[0].crossmatch.triage_status == adminapi.CrossmatchTriageStatus.RESOLVED
    assert response.records[0].crossmatch.candidates == [adminapi.RecordCrossmatchCandidate(pgc=1001)]
    assert response.records[1].id == "rec2"
    assert response.records[1].original_data == {"name": "B"}
    assert response.records[1].pgc == 1002
    assert response.records[1].crossmatch.triage_status == adminapi.CrossmatchTriageStatus.PENDING
    assert response.records[1].crossmatch.candidates == []


def test_get_records_passes_filters_to_fetch_records(
    get_records_manager: tuple[mock.MagicMock, domain.TableUploadManager],
) -> None:
    repo, manager = get_records_manager
    repo.fetch_records.return_value = []

    manager.get_records(adminapi.GetRecordsRequest(table_name="t", upload_status=adminapi.UploadStatus.UPLOADED))
    call_kw = repo.fetch_records.call_args[1]
    assert call_kw["has_pgc"] is True
    assert call_kw["pgc_value"] is None

    manager.get_records(adminapi.GetRecordsRequest(table_name="t", upload_status=adminapi.UploadStatus.PENDING))
    call_kw = repo.fetch_records.call_args[1]
    assert call_kw["has_pgc"] is False

    manager.get_records(adminapi.GetRecordsRequest(table_name="t", pgc=42))
    call_kw = repo.fetch_records.call_args[1]
    assert call_kw["has_pgc"] is None
    assert call_kw["pgc_value"] == 42

    manager.get_records(
        adminapi.GetRecordsRequest(table_name="t", triage_status=adminapi.CrossmatchTriageStatus.PENDING)
    )
    call_kw = repo.fetch_records.call_args[1]
    assert call_kw["triage_status"] == "pending"


def test_get_records_pagination(
    get_records_manager: tuple[mock.MagicMock, domain.TableUploadManager],
) -> None:
    repo, manager = get_records_manager
    repo.fetch_records.return_value = []

    manager.get_records(adminapi.GetRecordsRequest(table_name="t", page=2, page_size=10))
    call_kw = repo.fetch_records.call_args[1]
    assert call_kw["row_offset"] == 20
    assert call_kw["limit"] == 10


def test_get_records_pgc_none_when_missing(
    get_records_manager: tuple[mock.MagicMock, domain.TableUploadManager],
) -> None:
    repo, manager = get_records_manager
    repo.fetch_records.return_value = [
        model.TableRecord(
            id="rec1",
            original_data={"name": "A"},
            pgc=1001,
            triage_status="resolved",
            crossmatch_candidates=[],
        ),
        model.TableRecord(
            id="rec2",
            original_data={"name": "B"},
            pgc=None,
            triage_status="unprocessed",
            crossmatch_candidates=[],
        ),
    ]

    response = manager.get_records(adminapi.GetRecordsRequest(table_name="t", page=0, page_size=25))

    assert response.records[0].pgc == 1001
    assert response.records[1].pgc is None
