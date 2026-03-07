import os
import random
import time
import uuid

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

SMALL_CLUSTER_OBJECTS_NUM = 20
SMALL_CLUSTER_RADIUS = 20 / 3600
SMALL_CLUSTER_RA_CENTER = random.uniform(SMALL_CLUSTER_RADIUS, 360 - SMALL_CLUSTER_RADIUS)
SMALL_CLUSTER_DEC_CENTER = random.uniform(-90 + SMALL_CLUSTER_RADIUS, 90 - SMALL_CLUSTER_RADIUS)


@lib.test_logging_decorator
def create_marking(session: requests.Session, table_name: str):
    request_data = adminapi.CreateMarkingRequest(
        table_name=table_name,
        catalogs=[
            adminapi.CatalogToMark(
                name="icrs",
                parameters={
                    "ra": adminapi.ParameterToMark(column_name="ra"),
                    "dec": adminapi.ParameterToMark(column_name="dec"),
                    "e_ra": adminapi.ParameterToMark(column_name="e_ra"),
                    "e_dec": adminapi.ParameterToMark(column_name="e_dec"),
                },
                key=None,
                additional_params=None,
            ),
            adminapi.CatalogToMark(
                name="designation",
                parameters={
                    "design": adminapi.ParameterToMark(column_name="name"),
                },
                key=None,
                additional_params=None,
            ),
        ],
    )

    response = session.post("/v1/marking", json=request_data.model_dump(mode="json"))
    response.raise_for_status()


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


def get_record_ids(session: requests.Session, table_name: str, expected_count: int) -> list[str]:
    request_data = adminapi.GetRecordsRequest(table_name=table_name, page=0, page_size=expected_count * 2)
    response = session.get("/v1/records", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    records = response.json()["data"]["records"]
    return [r["id"] for r in records]


@lib.test_logging_decorator
def set_crossmatch(
    session: requests.Session,
    record_ids: list[str],
    kind: str,
):
    if kind == "new":
        request_data = adminapi.SetCrossmatchResultsRequest(
            statuses=adminapi.StatusesPayload(
                new=adminapi.NewStatusPayload(record_ids=record_ids),
            ),
        )
    elif kind == "existing":
        request_data = adminapi.SetCrossmatchResultsRequest(
            statuses=adminapi.StatusesPayload(
                existing=adminapi.ExistingStatusPayload(
                    record_ids=record_ids,
                    pgcs=[6775395 + i + 1 for i in range(len(record_ids))],
                ),
            ),
        )
    else:
        assert kind == "collided"
        request_data = adminapi.SetCrossmatchResultsRequest(
            statuses=adminapi.StatusesPayload(
                collided=adminapi.CollidedStatusPayload(
                    record_ids=record_ids,
                    possible_matches=[[6775395 + i + 1] for i in range(len(record_ids))],
                ),
            ),
        )
    response = session.post(
        "/v1/records/crossmatch",
        json=request_data.model_dump(mode="json"),
    )
    response.raise_for_status()


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
def check_table_info(session: requests.Session, table_name: str):
    request_data = adminapi.GetTableRequest(table_name=table_name)

    response = session.get("/v1/table", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    table_info = response.json()["data"]
    if table_info["statistics"] is None:
        raise ValueError("Processing status is None")

    assert table_info["statistics"]["new"] == OBJECTS_NUM


@lib.test_logging_decorator
def check_crossmatch_results(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.NEW,
        page_size=OBJECTS_NUM * 2,
    )

    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    crossmatch_data = response.json()["data"]

    assert len(crossmatch_data["records"]) == OBJECTS_NUM

    first_record = crossmatch_data["records"][0]

    request_data = adminapi.GetRecordCrossmatchRequest(record_id=first_record["record_id"])

    first_record_response = session.get("/v1/record/crossmatch", params=request_data.model_dump(mode="json"))
    first_record_response.raise_for_status()
    first_record_detail = first_record_response.json()["data"]
    assert first_record_detail["crossmatch"]["status"] == enums.RecordCrossmatchStatus.NEW

    for record in crossmatch_data["records"]:
        assert record["catalogs"]["coordinates"] is not None
        assert record["catalogs"]["designation"] is not None

        coords = record["catalogs"]["coordinates"]
        assert "equatorial" in coords
        assert "ra" in coords["equatorial"]
        assert "dec" in coords["equatorial"]
        assert "e_ra" in coords["equatorial"]
        assert "e_dec" in coords["equatorial"]

        designation = record["catalogs"]["designation"]
        assert "name" in designation
        assert designation["name"] is not None


@lib.test_logging_decorator
def overwrite_triage_via_set_crossmatch_and_verify(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.NEW,
        page_size=2,
    )
    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    records = response.json()["data"]["records"]
    assert len(records) >= 1
    record_id = records[0]["record_id"]

    set_request = adminapi.SetCrossmatchResultsRequest(
        statuses=adminapi.StatusesPayload(
            new=adminapi.NewStatusPayload(
                record_ids=[record_id],
                triage_statuses=[enums.RecordTriageStatus.PENDING],
            ),
        ),
    )
    response = session.post(
        "/v1/records/crossmatch",
        json=set_request.model_dump(mode="json"),
    )
    response.raise_for_status()

    detail_request = adminapi.GetRecordCrossmatchRequest(record_id=record_id)
    response = session.get("/v1/record/crossmatch", params=detail_request.model_dump(mode="json"))
    response.raise_for_status()
    detail = response.json()["data"]
    assert detail["crossmatch"]["triage_status"] == enums.RecordTriageStatus.PENDING


@lib.test_logging_decorator
def overwrite_designation_via_structured_and_verify(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.NEW,
        page_size=2,
    )
    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    records = response.json()["data"]["records"]
    assert len(records) >= 1
    record_id = records[0]["record_id"]

    overwrite_value = "OVERWRITTEN_STRUCTURED_TEST"
    structured_request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        units={},
        ids=[record_id],
        data=[[overwrite_value]],
    )
    response = session.post("/v1/data/structured", json=structured_request.model_dump(mode="json"))
    response.raise_for_status()

    detail_request = adminapi.GetRecordCrossmatchRequest(record_id=record_id)
    response = session.get("/v1/record/crossmatch", params=detail_request.model_dump(mode="json"))
    response.raise_for_status()
    detail = response.json()["data"]
    assert detail["crossmatch"]["catalogs"]["designation"]["name"] == overwrite_value


@lib.test_logging_decorator
def overwrite_icrs_via_structured_and_verify(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.NEW,
        page_size=3,
    )
    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()
    records = response.json()["data"]["records"]
    assert len(records) >= 2
    record_id = records[1]["record_id"]

    ra, dec, e_ra, e_dec = 100.0, 20.0, 0.5, 0.5
    structured_request = adminapi.SaveStructuredDataRequest(
        catalog="icrs",
        columns=["ra", "dec", "e_ra", "e_dec"],
        units={"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
        ids=[record_id],
        data=[[ra, dec, e_ra, e_dec]],
    )
    response = session.post("/v1/data/structured", json=structured_request.model_dump(mode="json"))
    response.raise_for_status()

    detail_request = adminapi.GetRecordCrossmatchRequest(record_id=record_id)
    response = session.get("/v1/record/crossmatch", params=detail_request.model_dump(mode="json"))
    response.raise_for_status()
    detail = response.json()["data"]
    eq = detail["crossmatch"]["catalogs"]["coordinates"]["equatorial"]
    assert abs(eq["ra"] - ra) < 1e-6 and abs(eq["dec"] - dec) < 1e-6
    assert abs(eq["e_ra"] - e_ra) < 1e-6 and abs(eq["e_dec"] - e_dec) < 1e-6


@lib.test_logging_decorator
def check_crossmatch_existing_results(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.EXISTING,
        page_size=OBJECTS_NUM * 2,
    )

    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    crossmatch_data = response.json()["data"]
    existing_records = crossmatch_data["records"]

    expected_min = int(OBJECTS_NUM * 0.8)
    assert len(existing_records) >= expected_min, (
        f"Expected at least {expected_min} existing records, got {len(existing_records)}"
    )

    for record in existing_records:
        assert record["catalogs"]["coordinates"] is not None
        assert record["catalogs"]["designation"] is not None
        assert record["metadata"]["pgc"] is not None

        coords = record["catalogs"]["coordinates"]
        assert "equatorial" in coords
        assert "ra" in coords["equatorial"]
        assert "dec" in coords["equatorial"]
        assert "e_ra" in coords["equatorial"]
        assert "e_dec" in coords["equatorial"]

        designation = record["catalogs"]["designation"]
        assert "name" in designation
        assert designation["name"] is not None


@lib.test_logging_decorator
def check_crossmatch_collided_results(session: requests.Session, table_name: str, expected_min_collided: int):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.COLLIDED,
        page_size=SMALL_CLUSTER_OBJECTS_NUM * 2,
    )

    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    crossmatch_data = response.json()["data"]
    collided_records = crossmatch_data["records"]

    assert len(collided_records) >= expected_min_collided, (
        f"Expected at least {expected_min_collided} collided records, got {len(collided_records)}"
    )

    for record in collided_records:
        assert record["catalogs"]["coordinates"] is not None
        assert record["catalogs"]["designation"] is not None

        coords = record["catalogs"]["coordinates"]
        assert "equatorial" in coords
        assert "ra" in coords["equatorial"]
        assert "dec" in coords["equatorial"]
        assert "e_ra" in coords["equatorial"]
        assert "e_dec" in coords["equatorial"]

        designation = record["catalogs"]["designation"]
        assert "name" in designation
        assert designation["name"] is not None


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
    adminapi = get_adminapi_session()
    dataapi = get_dataapi_session()

    test_seed = 42

    code = create_bibliography(adminapi)

    # ---- Create table with all `new` objects and upload it to layer 2 ----
    table_name = create_table(adminapi, code)
    upload_data(
        adminapi,
        table_name,
        objects_num=OBJECTS_NUM,
        ra_center=COORD_RA_CENTER,
        dec_center=COORD_DEC_CENTER,
        radius=COORD_RADIUS,
        seed=test_seed,
    )

    check_table_list(adminapi, table_name)
    check_get_table(adminapi, table_name, expected_columns=6, expected_rows=OBJECTS_NUM)

    create_marking(adminapi, table_name)
    start_marking(table_name)
    record_ids = get_record_ids(adminapi, table_name, OBJECTS_NUM)
    set_crossmatch(adminapi, record_ids, "new")

    check_table_info(adminapi, table_name)
    check_crossmatch_results(adminapi, table_name)
    overwrite_triage_via_set_crossmatch_and_verify(adminapi, table_name)
    overwrite_designation_via_structured_and_verify(adminapi, table_name)
    overwrite_icrs_via_structured_and_verify(adminapi, table_name)

    submit_crossmatch(table_name)
    layer2_import()

    check_dataapi_name_query(dataapi, "NGC")
    check_dataapi_coord_query(dataapi, COORD_RA_CENTER, COORD_DEC_CENTER, COORD_RADIUS / 2)
    check_dataapi_query(dataapi, "NGC")
    check_dataapi_query(dataapi, " ", page_size=10, page=0)

    # ---- Create table with all `existing` objects and upload it to layer 2 ----
    table_name_2 = create_table(adminapi, code)
    upload_data(
        adminapi,
        table_name_2,
        objects_num=OBJECTS_NUM,
        ra_center=COORD_RA_CENTER,
        dec_center=COORD_DEC_CENTER,
        radius=COORD_RADIUS,
        seed=test_seed,
    )
    upload_data(
        adminapi,
        table_name_2,
        objects_num=SMALL_CLUSTER_OBJECTS_NUM,
        ra_center=SMALL_CLUSTER_RA_CENTER,
        dec_center=SMALL_CLUSTER_DEC_CENTER,
        radius=SMALL_CLUSTER_RADIUS,
        seed=random.randint(0, 1000000),
    )

    create_marking(adminapi, table_name_2)
    start_marking(table_name_2)
    record_ids_2 = get_record_ids(adminapi, table_name_2, OBJECTS_NUM + SMALL_CLUSTER_OBJECTS_NUM)
    set_crossmatch(adminapi, record_ids_2, "existing")

    check_crossmatch_existing_results(adminapi, table_name_2)
    submit_crossmatch(table_name_2)
    layer2_import()

    # ---- Create table with `collided` objects ----
    table_name_3 = create_table(adminapi, code)
    upload_data(
        adminapi,
        table_name_3,
        objects_num=SMALL_CLUSTER_OBJECTS_NUM // 2,
        ra_center=SMALL_CLUSTER_RA_CENTER,
        dec_center=SMALL_CLUSTER_DEC_CENTER,
        radius=SMALL_CLUSTER_RADIUS,
        seed=random.randint(0, 1000000),
    )

    create_marking(adminapi, table_name_3)
    start_marking(table_name_3)
    record_ids_3 = get_record_ids(adminapi, table_name_3, SMALL_CLUSTER_OBJECTS_NUM // 2)
    set_crossmatch(adminapi, record_ids_3, "collided")

    check_crossmatch_collided_results(adminapi, table_name_3, expected_min_collided=SMALL_CLUSTER_OBJECTS_NUM // 4)
