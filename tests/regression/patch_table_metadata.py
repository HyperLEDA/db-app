import os
import uuid

import requests

from app.lib.storage import enums
from app.presentation import adminapi
from tests import lib

TABLE_DESCRIPTION_NEW = "Regression: patched table description"
COLUMN_DESCRIPTION_NEW = "Regression: patched column description"


def get_adminapi_session() -> lib.TestSession:
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8080")
    api_url = f"http://{api_host}:{api_port}/admin/api"
    return lib.TestSession(api_url)


@lib.test_logging_decorator
def upload_table(session: requests.Session) -> str:
    source_req = adminapi.CreateSourceRequest(authors=["Regression"], title=str(uuid.uuid4()), year=2026)
    source_resp = session.post("/v1/source", json=source_req.model_dump(mode="json"))
    source_resp.raise_for_status()
    bibcode = source_resp.json()["data"]["code"]

    table_name = f"patchmeta_{uuid.uuid4().hex[:8]}"
    create_req = adminapi.CreateTableRequest(
        table_name=table_name,
        columns=[
            adminapi.ColumnDescription(
                name="v",
                data_type=adminapi.DatatypeEnum["str"],
                ucd=None,
                unit=None,
                description=None,
            ),
        ],
        bibcode=bibcode,
        datatype=enums.DataType.REGULAR,
        description="",
    )
    create_resp = session.post("/v1/table", json=create_req.model_dump(mode="json"))
    create_resp.raise_for_status()

    add_req = adminapi.AddDataRequest(table_name=table_name, data=[{"v": "x"}])
    add_resp = session.post("/v1/table/data", json=add_req.model_dump(mode="json"))
    add_resp.raise_for_status()

    return table_name


@lib.test_logging_decorator
def patch_metadata_and_verify(session: requests.Session, table_name: str) -> None:
    patch_body = adminapi.PatchTableRequest(
        table_name=table_name,
        description=TABLE_DESCRIPTION_NEW,
        datatype=enums.DataType.PRELIMINARY,
        columns={
            "v": adminapi.PatchColumnSpec(description=COLUMN_DESCRIPTION_NEW),
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
    assert data["rows_num"] == 1

    v_col = next(c for c in data["column_info"] if c["name"] == "v")
    assert v_col["description"] == COLUMN_DESCRIPTION_NEW


@lib.test_logging_decorator
def run() -> None:
    session = get_adminapi_session()
    table_name = upload_table(session)
    patch_metadata_and_verify(session, table_name)
