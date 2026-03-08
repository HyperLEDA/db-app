import os
import random
import time
import uuid
from collections.abc import Sequence

import pandas
import requests

from app.commands.runtask import RunTaskCommand
from app.lib import commands
from app.lib.storage import enums
from app.presentation import adminapi
from tests import lib

random.seed(time.time())

OBJECTS_NUM = 50
COORD_RADIUS = 10
COORD_RA_CENTER = random.uniform(COORD_RADIUS, 360 - COORD_RADIUS)
COORD_DEC_CENTER = random.uniform(-90 + COORD_RADIUS, 90 - COORD_RADIUS)

TABLE2_OBJECTS_NUM = 20
TABLE2_RADIUS = 20 / 3600
TABLE2_RA_CENTER = random.uniform(TABLE2_RADIUS, 360 - TABLE2_RADIUS)
TABLE2_DEC_CENTER = random.uniform(-90 + TABLE2_RADIUS, 90 - TABLE2_RADIUS)


@lib.test_logging_decorator
def create_bibliography(session: requests.Session) -> str:
    request_data = adminapi.CreateSourceRequest(
        authors=["Doe, J."],
        title=str(uuid.uuid4()),
        year=2024,
    )

    response = session.post("/v1/source", json=request_data.model_dump(mode="json"))
    response.raise_for_status()
    return response.json()["data"]["code"]


@lib.test_logging_decorator
def create_table(session: requests.Session, bib_id: str) -> str:
    table_name = f"test_{str(uuid.uuid4())[:8]}"

    request_data = adminapi.CreateTableRequest(
        table_name=table_name,
        columns=[
            adminapi.ColumnDescription(
                name="name", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id", unit=None, description=None
            ),
            adminapi.ColumnDescription(
                name="ra",
                data_type=adminapi.DatatypeEnum["float"],
                unit="hourangle",
                ucd="pos.eq.ra",
                description=None,
            ),
            adminapi.ColumnDescription(
                name="dec", data_type=adminapi.DatatypeEnum["float"], unit="deg", ucd="pos.eq.dec", description=None
            ),
            adminapi.ColumnDescription(
                name="e_ra", data_type=adminapi.DatatypeEnum["float"], unit="deg", ucd=None, description=None
            ),
            adminapi.ColumnDescription(
                name="e_dec", data_type=adminapi.DatatypeEnum["float"], unit="deg", ucd=None, description=None
            ),
            adminapi.ColumnDescription(
                name="fuzz", data_type=adminapi.DatatypeEnum["str"], ucd=None, unit=None, description=None
            ),
        ],
        bibcode=bib_id,
        datatype=enums.DataType.REGULAR,
        description="",
    )

    response = session.post("/v1/table", json=request_data.model_dump(mode="json"))
    response.raise_for_status()

    return table_name


@lib.test_logging_decorator
def upload_data(
    session: requests.Session,
    table_name: str,
    objects_num: int,
    ra_center: float,
    dec_center: float,
    radius: float,
    seed: int,
):
    synthetic_data = lib.get_synthetic_data(
        objects_num,
        ra_center=ra_center,
        dec_center=dec_center,
        ra_range=radius,
        dec_range=radius,
        seed=seed,
    )
    df = pandas.DataFrame.from_records(synthetic_data)

    request_data = adminapi.AddDataRequest(
        table_name=table_name,
        data=df.to_dict("records"),  # type: ignore
    )

    response = session.post("/v1/table/data", json=request_data.model_dump(mode="json"))
    response.raise_for_status()


@lib.test_logging_decorator
def start_marking(table_name: str):
    commands.run(
        RunTaskCommand(
            "layer0-marking",
            input_data={"table_name": table_name, "batch_size": 200, "workers": 8},
            log_level="warn",
        ),
    )


def get_records(session: requests.Session, table_name: str, page_size: int) -> list[dict]:
    request_data = adminapi.GetRecordsRequest(table_name=table_name, page=0, page_size=page_size)
    response = session.get(
        "/v1/records",
        params=request_data.model_dump(mode="json", exclude_none=True),
    )
    response.raise_for_status()
    return response.json()["data"]["records"]


def get_record_ids(session: requests.Session, table_name: str, expected_count: int) -> list[str]:
    records = get_records(session, table_name, expected_count * 2)
    return [r["id"] for r in records]


@lib.test_logging_decorator
def fill_layer1_via_structured(session: requests.Session, records: list[dict]) -> None:
    ids = [r["id"] for r in records]
    orig = [r["original_data"] for r in records]

    designation_request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        units={},
        ids=ids,
        data=[[o["name"]] for o in orig],
    )
    response = session.post("/v1/data/structured", json=designation_request.model_dump(mode="json"))
    response.raise_for_status()

    ra_deg = 15.0
    icrs_request = adminapi.SaveStructuredDataRequest(
        catalog="icrs",
        columns=["ra", "dec", "e_ra", "e_dec"],
        units={"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
        ids=ids,
        data=[[float(o["ra"]) * ra_deg, float(o["dec"]), float(o["e_ra"]), float(o["e_dec"])] for o in orig],
    )
    response = session.post("/v1/data/structured", json=icrs_request.model_dump(mode="json"))
    response.raise_for_status()


@lib.test_logging_decorator
def check_layer1_via_records(session: requests.Session, table_name: str, expected_count: int) -> None:
    records = get_records(session, table_name, expected_count * 2)
    assert len(records) == expected_count, f"Expected {expected_count} records, got {len(records)}"
    for record in records:
        _assert_record_catalogs(record)


@lib.test_logging_decorator
def set_crossmatch_new(
    session: requests.Session,
    record_ids: list[str],
    triage_statuses: Sequence[enums.RecordTriageStatus | None],
):
    request_data = adminapi.SetCrossmatchResultsRequest(
        statuses=adminapi.StatusesPayload(
            new=adminapi.NewStatusPayload(
                record_ids=record_ids,
                triage_statuses=list(triage_statuses),
            ),
        ),
    )
    response = session.post(
        "/v1/records/crossmatch",
        json=request_data.model_dump(mode="json"),
    )
    response.raise_for_status()


def get_records_by_triage(
    session: requests.Session,
    table_name: str,
    triage_status: adminapi.CrossmatchTriageStatus,
    page_size: int,
) -> list[dict]:
    request_data = adminapi.GetRecordsRequest(
        table_name=table_name,
        page=0,
        page_size=page_size,
        triage_status=triage_status,
    )
    response = session.get("/v1/records", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    return response.json()["data"]["records"]


def get_records_by_upload_status(
    session: requests.Session,
    table_name: str,
    upload_status: adminapi.UploadStatus,
    page_size: int,
) -> list[dict]:
    request_data = adminapi.GetRecordsRequest(
        table_name=table_name,
        page=0,
        page_size=page_size,
        upload_status=upload_status,
    )
    response = session.get("/v1/records", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    return response.json()["data"]["records"]


def _assert_record_catalogs(record: dict) -> None:
    assert record["catalogs"]["icrs"] is not None
    assert record["catalogs"]["designation"] is not None
    icrs = record["catalogs"]["icrs"]
    assert "ra" in icrs and "dec" in icrs and "ra_error" in icrs and "dec_error" in icrs
    designation = record["catalogs"]["designation"]
    assert "name" in designation and designation["name"] is not None


@lib.test_logging_decorator
def check_triage_via_records(
    session: requests.Session,
    table_name: str,
    expected_pending: int,
    expected_resolved: int,
):
    pending_records = get_records_by_triage(
        session, table_name, adminapi.CrossmatchTriageStatus.PENDING, OBJECTS_NUM * 2
    )
    resolved_records = get_records_by_triage(
        session, table_name, adminapi.CrossmatchTriageStatus.RESOLVED, OBJECTS_NUM * 2
    )
    assert len(pending_records) == expected_pending, (
        f"Expected {expected_pending} pending records, got {len(pending_records)}"
    )
    assert len(resolved_records) == expected_resolved, (
        f"Expected {expected_resolved} resolved records, got {len(resolved_records)}"
    )
    for record in pending_records + resolved_records:
        _assert_record_catalogs(record)


@lib.test_logging_decorator
def check_pgc_after_submit_via_records(
    session: requests.Session,
    table_name: str,
    expected_with_pgc: int,
    expected_without_pgc: int,
):
    records_with_pgc = get_records_by_upload_status(
        session, table_name, adminapi.UploadStatus.UPLOADED, OBJECTS_NUM * 2
    )
    pending_records = get_records_by_triage(
        session, table_name, adminapi.CrossmatchTriageStatus.PENDING, OBJECTS_NUM * 2
    )
    assert len(records_with_pgc) == expected_with_pgc, (
        f"Expected {expected_with_pgc} records with pgc, got {len(records_with_pgc)}"
    )
    assert len(pending_records) == expected_without_pgc, (
        f"Expected {expected_without_pgc} pending records (no pgc), got {len(pending_records)}"
    )
    for record in records_with_pgc:
        assert record.get("pgc") is not None
        _assert_record_catalogs(record)
    for record in pending_records:
        assert record.get("pgc") is None
        _assert_record_catalogs(record)


@lib.test_logging_decorator
def check_table_list(session: requests.Session, table_name: str):
    response = session.get("/v1/tables", params={"query": table_name})
    response.raise_for_status()
    data = response.json()["data"]
    assert "tables" in data
    tables_list = data["tables"]
    matching = [t for t in tables_list if t["name"] == table_name]
    assert len(matching) >= 1, f"Expected at least one table with name {table_name}"
    for item in tables_list:
        assert "name" in item
        assert "description" in item
        assert "num_entries" in item
        assert "num_fields" in item


@lib.test_logging_decorator
def check_get_table(session: requests.Session, table_name: str, expected_columns: int, expected_rows: int):
    request_data = adminapi.GetTableRequest(table_name=table_name)
    response = session.get("/v1/table", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    table_info = response.json()["data"]
    assert "id" in table_info
    assert "description" in table_info
    assert "column_info" in table_info
    assert len(table_info["column_info"]) == expected_columns
    assert table_info["rows_num"] == expected_rows
    assert "bibliography" in table_info
    assert "meta" in table_info


@lib.test_logging_decorator
def submit_crossmatch(table_name: str):
    commands.run(
        RunTaskCommand(
            "submit-crossmatch",
            input_data={"table_name": table_name, "batch_size": OBJECTS_NUM // 2},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator
def layer2_import():
    commands.run(
        RunTaskCommand(
            "layer2-import",
            input_data={"batch_size": OBJECTS_NUM // 5, "silent": True},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator
def check_dataapi_name_query(session: lib.TestSession, name_prefix: str):
    response = session.get("/v1/query/simple", params={"name": name_prefix, "page_size": 100})
    response.raise_for_status()
    name_results = response.json()["data"]

    assert len(name_results["objects"]) > 0

    for obj in name_results["objects"]:
        if "designation" in obj and "name" in obj["designation"]:
            assert obj["designation"]["name"].startswith("NGC")


@lib.test_logging_decorator
def check_dataapi_coord_query(session: lib.TestSession, ra: float, dec: float, radius: float):
    response = session.get("/v1/query/simple", params={"ra": ra, "dec": dec, "radius": radius, "page_size": 100})
    response.raise_for_status()
    coord_results = response.json()["data"]

    assert len(coord_results["objects"]) > 0


@lib.test_logging_decorator
def check_dataapi_query(session: lib.TestSession, q: str, page_size: int = 10, page: int = 0):
    response = session.get("/v1/query", params={"q": q, "page_size": page_size, "page": page})
    response.raise_for_status()
    data = response.json()["data"]
    assert "objects" in data


def get_adminapi_session() -> lib.TestSession:
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8080")
    api_url = f"http://{api_host}:{api_port}/admin/api"
    return lib.TestSession(api_url)


def get_dataapi_session() -> lib.TestSession:
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8081")
    api_url = f"http://{api_host}:{api_port}/api"
    return lib.TestSession(api_url)


def run():
    adminapi_session = get_adminapi_session()
    dataapi = get_dataapi_session()

    test_seed = 42

    code = create_bibliography(adminapi_session)

    # ---- Table 1: all new rows, mark as resolved via POST /crossmatch, submit ----
    table_name = create_table(adminapi_session, code)
    upload_data(
        adminapi_session,
        table_name,
        objects_num=OBJECTS_NUM,
        ra_center=COORD_RA_CENTER,
        dec_center=COORD_DEC_CENTER,
        radius=COORD_RADIUS,
        seed=test_seed,
    )

    check_table_list(adminapi_session, table_name)
    check_get_table(adminapi_session, table_name, expected_columns=6, expected_rows=OBJECTS_NUM)

    records = get_records(adminapi_session, table_name, OBJECTS_NUM * 2)
    fill_layer1_via_structured(adminapi_session, records)
    check_layer1_via_records(adminapi_session, table_name, OBJECTS_NUM)

    record_ids = [r["id"] for r in records]
    set_crossmatch_new(
        adminapi_session,
        record_ids,
        triage_statuses=[enums.RecordTriageStatus.RESOLVED] * len(record_ids),
    )

    submit_crossmatch(table_name)
    layer2_import()

    check_dataapi_name_query(dataapi, "NGC")
    check_dataapi_coord_query(dataapi, COORD_RA_CENTER, COORD_DEC_CENTER, COORD_RADIUS / 2)
    check_dataapi_query(dataapi, "NGC")
    check_dataapi_query(dataapi, " ", page_size=10, page=0)

    # ---- Table 2: smaller cluster, some pending/resolved; check via /records; submit; check pgc ----
    table_name_2 = create_table(adminapi_session, code)
    upload_data(
        adminapi_session,
        table_name_2,
        objects_num=TABLE2_OBJECTS_NUM,
        ra_center=TABLE2_RA_CENTER,
        dec_center=TABLE2_DEC_CENTER,
        radius=TABLE2_RADIUS,
        seed=test_seed + 1,
    )

    records_2 = get_records(adminapi_session, table_name_2, TABLE2_OBJECTS_NUM * 2)
    fill_layer1_via_structured(adminapi_session, records_2)
    check_layer1_via_records(adminapi_session, table_name_2, TABLE2_OBJECTS_NUM)

    record_ids_2 = [r["id"] for r in records_2]

    n_pending = TABLE2_OBJECTS_NUM // 2
    n_resolved = TABLE2_OBJECTS_NUM - n_pending
    set_crossmatch_new(
        adminapi_session,
        record_ids_2,
        triage_statuses=[enums.RecordTriageStatus.PENDING] * n_pending
        + [enums.RecordTriageStatus.RESOLVED] * n_resolved,
    )

    check_triage_via_records(adminapi_session, table_name_2, expected_pending=n_pending, expected_resolved=n_resolved)

    submit_crossmatch(table_name_2)

    check_pgc_after_submit_via_records(
        adminapi_session, table_name_2, expected_with_pgc=n_resolved, expected_without_pgc=n_pending
    )
