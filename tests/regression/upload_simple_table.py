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
def upload_data(session: requests.Session, table_id: int, num_records: int = 50):
    synthetic_data = lib.generate_synthetic_astronomical_data(num_records)
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
        ),
    )


@lib.test_logging_decorator(__file__)
def start_crossmatch(table_name: str):
    commands.run(
        RunTaskCommand(
            "crossmatch",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name},
        ),
    )


@lib.test_logging_decorator(__file__)
def get_table_info(session: requests.Session, table_name: str) -> dict[str, int]:
    request_data = adminapi.GetTableRequest(table_name=table_name)

    response = session.get("/v1/table", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    table_info = response.json()["data"]
    if table_info["statistics"] is None:
        raise ValueError("Processing status is None")

    return table_info["statistics"]


@lib.test_logging_decorator(__file__)
def get_crossmatch_results(session: requests.Session, table_name: str) -> dict:
    request_data = adminapi.GetRecordsCrossmatchRequest(
        table_name=table_name,
        status=enums.RecordCrossmatchStatus.NEW,
        page_size=100,
    )

    response = session.get("/v1/records/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    return response.json()["data"]


@lib.test_logging_decorator(__file__)
def get_record_crossmatch(session: requests.Session, record_id: str) -> dict:
    request_data = adminapi.GetRecordCrossmatchRequest(record_id=record_id)

    response = session.get("/v1/record/crossmatch", params=request_data.model_dump(mode="json"))
    response.raise_for_status()

    return response.json()["data"]


@lib.test_logging_decorator(__file__)
def submit_crossmatch(table_name: str):
    commands.run(
        RunTaskCommand(
            "submit-crossmatch",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name, "batch_size": 10},
        ),
    )


@lib.test_logging_decorator(__file__)
def layer2_import():
    commands.run(
        RunTaskCommand(
            "layer2-import",
            "configs/dev/tasks.yaml",
            input_data={"batch_size": 10},
        ),
    )


def run():
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8080")
    api_url = f"http://{api_host}:{api_port}/admin/api"
    session = lib.TestSession(api_url)

    code = create_bibliography(session)
    table_id, table_name = create_table(session, code)
    upload_data(session, table_id)

    create_marking(session, table_name)
    start_marking(table_name)
    start_crossmatch(table_name)

    statuses_data = get_table_info(session, table_name)
    assert statuses_data["new"] == 50

    crossmatch_data = get_crossmatch_results(session, table_name)
    assert len(crossmatch_data["records"]) == statuses_data["new"]

    first_record = crossmatch_data["records"][0]
    first_record_detail = get_record_crossmatch(session, first_record["record_id"])
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

    submit_crossmatch(table_name)
    layer2_import()
