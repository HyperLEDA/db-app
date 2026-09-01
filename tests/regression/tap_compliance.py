import os

import requests

from tests import lib


def get_dataapi_session() -> lib.TestSession:
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8081")
    api_url = f"http://{api_host}:{api_port}/api"
    return lib.TestSession(api_url)


@lib.test_logging_decorator
def check_tap_tables(session: requests.Session) -> None:
    response = session.get("/v1/tap/tables")
    response.raise_for_status()
    schemas = response.json()["data"]["schemas"]
    assert isinstance(schemas, list)
    assert len(schemas) > 0
    for schema in schemas:
        tables = schema["tables"]
        assert isinstance(tables, list)
        assert len(tables) > 0


@lib.test_logging_decorator
def check_tap_sync(session: requests.Session) -> None:
    response = session.get(
        "/v1/tap/sync",
        params={
            "query": "SELECT pgc, ra, dec FROM icrs ORDER BY pgc",
            "lang": "PostgreSQL",
            "format": "json",
            "maxrec": 5,
        },
    )
    response.raise_for_status()
    table = response.json()["data"]["resource"]["table"]
    assert [c["name"] for c in table["columns"]] == ["pgc", "ra", "dec"]
    assert table["columns"][0]["datatype"] == "int"
    assert table["columns"][1]["datatype"] == "double"
    assert table["columns"][2]["datatype"] == "double"
    assert len(table["data"]) == 5
    assert all(len(row) == 3 for row in table["data"])


def run() -> None:
    session = get_dataapi_session()
    check_tap_tables(session)
    check_tap_sync(session)
