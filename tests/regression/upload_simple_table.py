import uuid

import requests

from app.lib import testing


def test_decorator(func):
    f = testing.test_status_decorator(func)
    return testing.test_logging_decorator(f, __file__)


@test_decorator
def create_bibliography(session: requests.Session) -> requests.Response:
    return session.post(
        "/api/v1/admin/source",
        json={
            "authors": ["Doe, J."],
            "title": str(uuid.uuid4()),
            "year": 2024,
        },
    )


@test_decorator
def create_table(session: requests.Session, bib_id: str) -> requests.Response:
    return session.post(
        "/api/v1/admin/table",
        json={
            "table_name": f"test_{str(uuid.uuid4())}",
            "columns": [
                {"name": "name", "data_type": "str", "ucd": "meta.id"},
                {"name": "ra", "data_type": "float", "unit": "hourangle", "ucd": "pos.eq.ra"},
                {"name": "dec", "data_type": "float", "unit": "deg", "ucd": "pos.eq.dec"},
                {"name": "fuzz", "data_type": "str"},
            ],
            "bibcode": bib_id,
        },
    )


@test_decorator
def upload_data(session: requests.Session, table_id: str) -> requests.Response:
    return session.post(
        "/api/v1/admin/table/data",
        json={
            "table_id": table_id,
            "data": [
                {"name": "M 33", "ra": 1.5641, "dec": 30.6602, "fuzz": str(uuid.uuid4())},
                {"name": "M 31", "ra": 0.7123, "dec": 41.269, "fuzz": str(uuid.uuid4())},
            ],
        },
    )


@test_decorator
def start_processing(session: requests.Session, table_id: str) -> requests.Response:
    return session.post(
        "/api/v1/admin/table/process",
        json={
            "table_id": table_id,
        },
    )


@test_decorator
def get_object_statuses(session: requests.Session, table_id: str) -> requests.Response:
    return session.get("/api/v1/table/status/stats", params={"table_id": table_id})


@test_decorator
def set_table_status(session: requests.Session, table_id: str) -> requests.Response:
    return session.post(
        "/api/v1/admin/table/status",
        json={"table_id": table_id},
    )


def run():
    session = testing.TestSession("http://localhost:8080")

    create_bibliography_data = create_bibliography(session)
    create_table_data = create_table(session, create_bibliography_data.json()["data"]["code"])
    table_id = create_table_data.json()["data"]["id"]

    upload_data(session, table_id)
    start_processing(session, table_id)

    statuses_data = get_object_statuses(session, table_id)
    assert statuses_data.json()["data"]["processing"]["new"] == 2

    set_table_status(session, table_id)
