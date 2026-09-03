import datetime
import uuid
from unittest import mock

import pytest
import structlog
from psycopg import sql

from app.adminapi import repository
from app.lib.storage import enums
from tests import lib


def normalize_query(s: str | sql.Composable) -> str:
    if not isinstance(s, str):
        s = s.as_string(None)
    return " ".join(s.replace("\n", " ").replace(", ", ",").lower().split())


@pytest.fixture
def storage_repo() -> tuple[mock.MagicMock, repository.Repository]:
    storage_mock = mock.MagicMock()
    repo = repository.Repository(storage_mock, structlog.get_logger())
    return storage_mock, repo


@pytest.mark.parametrize(
    "kwargs,expected_query",
    [
        ({}, 'SELECT * FROM "rawdata"."ironman"'),
        ({"columns": ["one", "two"]}, 'SELECT "one","two" FROM "rawdata"."ironman"'),
        (
            {"order_column": "one", "order_direction": "desc"},
            'SELECT * FROM "rawdata"."ironman" ORDER BY "one" DESC',
        ),
        ({"limit": 10}, 'SELECT * FROM "rawdata"."ironman" LIMIT %s'),
        (
            {"offset": uuid.uuid4()},
            'SELECT * FROM "rawdata"."ironman" WHERE "hyperleda_internal_id" > %s',
        ),
        (
            {
                "columns": ["one", "two"],
                "order_column": "one",
                "order_direction": "desc",
                "offset": uuid.uuid4(),
                "limit": 10,
            },
            'SELECT "one","two" FROM "rawdata"."ironman" WHERE "hyperleda_internal_id" > %s'
            ' ORDER BY "one" DESC LIMIT %s',
        ),
    ],
    ids=["no kwargs", "with columns", "with order by", "with limit", "with offset", "with all"],
)
def test_fetch_raw_data(
    storage_repo: tuple[mock.MagicMock, repository.Repository],
    kwargs: dict,
    expected_query: str,
) -> None:
    storage_mock, repo = storage_repo
    lib.returns(storage_mock.query, {"haha": [1, 2]})

    repo.fetch_raw_data("ironman", **kwargs)
    call_args = storage_mock.query.call_args
    assert call_args is not None
    args, _ = call_args

    actual = normalize_query(args[0])
    expected = normalize_query(expected_query)

    assert actual == expected


def test_search_tables_calls_query_with_expected_structure(
    storage_repo: tuple[mock.MagicMock, repository.Repository],
) -> None:
    storage_mock, repo = storage_repo
    storage_mock.query.return_value = [
        {
            "table_name": "my_table",
            "status": enums.TableStatus.INITIATED,
            "description": "A test table",
            "num_fields": 6,
            "modification_dt": datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
            "bibcode": "2024PDU....4601628D",
        }
    ]

    result = repo.search_tables(
        "my_table",
        page_size=25,
        page=1,
        statuses=[enums.TableStatus.INITIATED],
    )

    storage_mock.query.assert_called_once()
    query = storage_mock.query.call_args[0][0]
    params = storage_mock.query.call_args[1]["params"]

    assert "layer0.tables" in query
    assert "meta.table_info" in query
    assert "ILIKE" in query
    assert "t.status = ANY" in query
    assert "LIMIT" in query
    assert "OFFSET" in query
    assert params[-3] == [enums.TableStatus.INITIATED]
    assert params[-2] == 25
    assert params[-1] == 25
    assert len(result) == 1
    assert result[0].table_name == "my_table"
    assert result[0].description == "A test table"
    assert result[0].num_fields == 6
    assert result[0].status == enums.TableStatus.INITIATED
