import requests

from app.lib.storage import enums
from app.presentation import adminapi
from tests import lib
from tests.regression import upload_simple_table

ROW_COUNT = 5
TABLE_DESCRIPTION_NEW = "Regression: patched table description"
NAME_COLUMN_DESCRIPTION_NEW = "Regression: patched name column description"


@lib.test_logging_decorator
def upload_table(session: requests.Session) -> str:
    bib = upload_simple_table.create_bibliography(session)
    table_name = upload_simple_table.create_table(session, bib)
    upload_simple_table.upload_data(
        session,
        table_name,
        objects_num=ROW_COUNT,
        ra_center=100.0,
        dec_center=20.0,
        radius=2.0,
        seed=12345,
    )
    return table_name


@lib.test_logging_decorator
def patch_metadata_and_verify(session: requests.Session, table_name: str) -> None:
    patch_body = adminapi.PatchTableRequest(
        table_name=table_name,
        description=TABLE_DESCRIPTION_NEW,
        datatype=enums.DataType.PRELIMINARY,
        columns={
            "name": adminapi.PatchColumnSpec(description=NAME_COLUMN_DESCRIPTION_NEW),
        },
    )
    patch_resp = session.patch("/v1/table", json=patch_body.model_dump(mode="json"))
    patch_resp.raise_for_status()

    get_req = adminapi.GetTableRequest(table_name=table_name)
    get_resp = session.get("/v1/table", params=get_req.model_dump(mode="json"))
    get_resp.raise_for_status()
    data = get_resp.json()["data"]

    assert data["description"] == TABLE_DESCRIPTION_NEW
    assert data["meta"]["datatype"] == enums.DataType.PRELIMINARY.value
    assert data["rows_num"] == ROW_COUNT

    name_col = next(c for c in data["column_info"] if c["name"] == "name")
    assert name_col["description"] == NAME_COLUMN_DESCRIPTION_NEW


@lib.test_logging_decorator
def run() -> None:
    session = upload_simple_table.get_adminapi_session()
    table_name = upload_table(session)
    patch_metadata_and_verify(session, table_name)
