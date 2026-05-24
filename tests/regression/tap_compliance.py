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


def run() -> None:
    session = get_dataapi_session()
    check_tap_tables(session)
