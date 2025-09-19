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
COORD_RA_CENTER = 45.5
COORD_DEC_CENTER = 50
COORD_RADIUS = 1


@lib.test_logging_decorator(__file__)
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


@lib.test_logging_decorator(__file__)
def create_bibliography(session: requests.Session) -> str:
    request_data = adminapi.CreateSourceRequest(
        authors=["Doe, J."],
        title=str(uuid.uuid4()),
        year=2024,
    )

    response = session.post("/v1/source", json=request_data.model_dump(mode="json"))
    response.raise_for_status()
    return response.json()["data"]["code"]


@lib.test_logging_decorator(__file__)
def create_table(session: requests.Session, bib_id: str) -> tuple[int, str]:
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
    table_id = response.json()["data"]["id"]

    return table_id, table_name


@lib.test_logging_decorator(__file__)
def upload_data(
    session: requests.Session,
    table_id: int,
    objects_num: int,
    ra_center: float,
    dec_center: float,
    radius: float,
):
    synthetic_data = lib.get_synthetic_data(
        objects_num,
        ra_center=ra_center,
        dec_center=dec_center,
        ra_range=radius,
        dec_range=radius,
    )
    df = pandas.DataFrame.from_records(synthetic_data)

    request_data = adminapi.AddDataRequest(
        table_id=table_id,
        data=df.to_dict("records"),  # type: ignore
    )

    response = session.post("/v1/table/data", json=request_data.model_dump(mode="json"))
    response.raise_for_status()


@lib.test_logging_decorator(__file__)
def start_marking(table_name: str):
    commands.run(
        RunTaskCommand(
            "layer0-marking",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name, "batch_size": 200, "workers": 8},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator(__file__)
def start_crossmatch(table_name: str):
    commands.run(
        RunTaskCommand(
            "crossmatch",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator(__file__)
def check_table_info(session: requests.Session, table_name: str):
    request_data = adminapi.GetTableRequest(table_name=table_name)

    response = session.get("/v1/table", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    table_info = response.json()["data"]
    if table_info["statistics"] is None:
        raise ValueError("Processing status is None")

    assert table_info["statistics"]["new"] == OBJECTS_NUM


@lib.test_logging_decorator(__file__)
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


@lib.test_logging_decorator(__file__)
def submit_crossmatch(table_name: str):
    commands.run(
        RunTaskCommand(
            "submit-crossmatch",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name, "batch_size": OBJECTS_NUM // 2},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator(__file__)
def layer2_import():
    commands.run(
        RunTaskCommand(
            "layer2-import",
            "configs/dev/tasks.yaml",
            input_data={"batch_size": OBJECTS_NUM // 5},
            log_level="warn",
        ),
    )


@lib.test_logging_decorator(__file__)
def check_dataapi_name_query(session: lib.TestSession, name_prefix: str):
    response = session.get("/v1/query/simple", params={"name": name_prefix, "page_size": 100})
    response.raise_for_status()
    name_results = response.json()["data"]

    assert len(name_results["objects"]) > 0

    for obj in name_results["objects"]:
        if "designation" in obj and "name" in obj["designation"]:
            assert obj["designation"]["name"].startswith("NGC")


@lib.test_logging_decorator(__file__)
def check_dataapi_coord_query(session: lib.TestSession, ra: float, dec: float, radius: float):
    response = session.get("/v1/query/simple", params={"ra": ra, "dec": dec, "radius": radius, "page_size": 100})
    response.raise_for_status()
    coord_results = response.json()["data"]

    assert len(coord_results["objects"]) > 0


@lib.test_logging_decorator(__file__)
def check_crossmatch_collisions(session: requests.Session, table_name: str):
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.COLLIDED,
        page_size=OBJECTS_NUM * 10,
    )

    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    crossmatch_data = response.json()["data"]
    collision_count = len(crossmatch_data["records"])

    assert collision_count > 0, f"Expected collisions in table {table_name}, but found {collision_count}"

    for record in crossmatch_data["records"]:
        assert record["status"] == enums.RecordCrossmatchStatus.COLLIDED
        assert record["catalogs"]["coordinates"] is not None
        assert record["catalogs"]["designation"] is not None


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

    code = create_bibliography(adminapi)
    table_id, table_name = create_table(adminapi, code)
    upload_data(
        adminapi,
        table_id,
        objects_num=OBJECTS_NUM,
        ra_center=COORD_RA_CENTER,
        dec_center=COORD_DEC_CENTER,
        radius=COORD_RADIUS,
    )

    create_marking(adminapi, table_name)
    start_marking(table_name)
    start_crossmatch(table_name)

    check_table_info(adminapi, table_name)
    check_crossmatch_results(adminapi, table_name)

    submit_crossmatch(table_name)
    layer2_import()

    check_dataapi_name_query(dataapi, "NGC")
    check_dataapi_coord_query(dataapi, COORD_RA_CENTER, COORD_DEC_CENTER, COORD_RADIUS / 2)

    table_id, table_name = create_table(adminapi, code)
    # generate a lot of objects in the same place so there will be guarateed collisions
    upload_data(
        adminapi,
        table_id,
        objects_num=OBJECTS_NUM * 10,
        ra_center=COORD_RA_CENTER,
        dec_center=COORD_DEC_CENTER,
        radius=COORD_RADIUS,
    )

    create_marking(adminapi, table_name)
    start_marking(table_name)
    start_crossmatch(table_name)

    check_crossmatch_collisions(adminapi, table_name)
