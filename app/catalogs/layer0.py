from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import Any

from psycopg import sql

from app.lib.storage import postgres

RAWDATA_SCHEMA = "rawdata"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"


def require_table_id(storage: postgres.PgStorage, table_name: str) -> int:
    try:
        row = storage.query_one(
            "SELECT id FROM layer0.tables WHERE table_name = %s",
            params=[table_name],
        )
    except RuntimeError as e:
        raise RuntimeError(f"table {table_name!r} is not in layer0.tables") from e
    return int(row["id"])


@contextmanager
def rawdata_table(
    storage: postgres.PgStorage,
    *,
    table_name: str | None = None,
    record_ids: Sequence[str] | None = None,
) -> Generator[list[int]]:
    if (table_name is None) == (record_ids is None):
        raise ValueError("provide exactly one of table_name or record_ids")

    if table_name is not None:
        table_ids = [require_table_id(storage, table_name)]
    elif not record_ids:
        table_ids = []
    else:
        rows = storage.query(
            "SELECT DISTINCT table_id FROM layer0.records WHERE id = ANY(%s)",
            params=[list(record_ids)],
        )
        table_ids = [int(row["table_id"]) for row in rows]

    yield table_ids
    if table_ids:
        storage.exec(
            "UPDATE layer0.tables SET modification_dt = now() WHERE id = ANY(%s)",
            params=[table_ids],
        )


def touch_pgcs(storage: postgres.PgStorage, pgc_ids: Sequence[int]) -> None:
    if not pgc_ids:
        return
    storage.exec(
        "UPDATE common.pgc SET modification_time = NOW() WHERE id = ANY(%s)",
        params=[list(pgc_ids)],
    )


def build_raw_table_select(
    table_name: str,
    columns: list[str] | None = None,
    offset: str | None = None,
    order_column: str | None = None,
    order_direction: str = "asc",
    limit: int | None = None,
    row_offset: int | None = None,
) -> tuple[sql.Composed, list[Any]]:
    if columns:
        columns_sql = sql.SQL(",").join([sql.Identifier(c) for c in columns])
    else:
        columns_sql = sql.SQL("*")

    params: list[Any] = []
    where_parts: list[sql.Composable] = []

    if offset is not None:
        where_parts.append(
            sql.SQL("{} > %s").format(
                sql.Identifier(INTERNAL_ID_COLUMN_NAME),
            )
        )
        params.append(offset)

    parts: list[sql.Composable] = [
        sql.SQL("SELECT {} FROM {}.{}").format(
            columns_sql,
            sql.Identifier(RAWDATA_SCHEMA),
            sql.Identifier(table_name),
        )
    ]

    if where_parts:
        parts.append(sql.SQL(" WHERE "))
        parts.append(sql.SQL(" AND ").join(where_parts))

    if order_column is not None:
        if order_direction not in ("asc", "desc"):
            raise ValueError(f"invalid order direction: {order_direction}")
        parts.append(sql.SQL(" ORDER BY {} ").format(sql.Identifier(order_column)))
        parts.append(sql.SQL(order_direction))
    elif row_offset is not None:
        parts.append(
            sql.SQL(" ORDER BY {} ").format(
                sql.Identifier(INTERNAL_ID_COLUMN_NAME),
            )
        )

    if limit is not None:
        parts.append(sql.SQL(" LIMIT %s"))
        params.append(limit)

    if row_offset is not None:
        parts.append(sql.SQL(" OFFSET %s"))
        params.append(row_offset)

    return sql.Composed(parts), params
