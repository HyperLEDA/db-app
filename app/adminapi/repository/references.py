import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, final

import psycopg
import structlog
from psycopg import rows, sql

from app.lib.storage import postgres
from app.lib.storage.postgres.postgres_storage import PgStorage

_REFERENCE_TABLE_METADATA_QUERY = """
WITH t AS (
  SELECT %s::text AS schema_name, %s::text AS table_name
)
SELECT
  c.column_name,
  c.data_type::text AS data_type,
  c.udt_name::text AS udt_name,
  (c.is_nullable = 'NO') AS not_null,
  c.column_default,
  (pk.column_name IS NOT NULL) AS is_primary_key,
  pk.ordinal_position AS primary_key_position,
  ti.param->>'description' AS table_description,
  ci.param->>'description' AS description,
  fk.foreign_table_schema,
  fk.foreign_table_name,
  fk.foreign_column_name
FROM t
JOIN information_schema.columns AS c
  ON c.table_schema = t.schema_name
 AND c.table_name = t.table_name
LEFT JOIN meta.column_info AS ci
  ON ci.schema_name = t.schema_name
 AND ci.table_name = t.table_name
 AND ci.column_name = c.column_name
LEFT JOIN meta.table_info AS ti
  ON ti.schema_name = t.schema_name
 AND ti.table_name = t.table_name
LEFT JOIN (
  SELECT
    kcu.column_name,
    kcu.ordinal_position
  FROM t
  JOIN information_schema.table_constraints AS tc
    ON tc.table_schema = t.schema_name
   AND tc.table_name = t.table_name
   AND tc.constraint_type = 'PRIMARY KEY'
  JOIN information_schema.key_column_usage AS kcu
    ON kcu.constraint_schema = tc.constraint_schema
   AND kcu.constraint_name = tc.constraint_name
   AND kcu.table_schema = tc.table_schema
   AND kcu.table_name = tc.table_name
) AS pk ON pk.column_name = c.column_name
LEFT JOIN (
  SELECT
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
  FROM t
  JOIN information_schema.table_constraints AS tc
    ON tc.table_schema = t.schema_name
   AND tc.table_name = t.table_name
   AND tc.constraint_type = 'FOREIGN KEY'
  JOIN information_schema.key_column_usage AS kcu
    ON kcu.constraint_schema = tc.constraint_schema
   AND kcu.constraint_name = tc.constraint_name
   AND kcu.table_schema = tc.table_schema
   AND kcu.table_name = tc.table_name
  JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_schema = tc.constraint_schema
   AND ccu.constraint_name = tc.constraint_name
) AS fk ON fk.column_name = c.column_name
ORDER BY c.ordinal_position
"""

_ENUM_VALUES_QUERY = """
SELECT e.enumlabel
FROM pg_type AS pt
JOIN pg_namespace AS pn ON pn.oid = pt.typnamespace
JOIN pg_enum AS e ON e.enumtypid = pt.oid
WHERE pn.nspname = %s
  AND pt.typname = %s
ORDER BY e.enumsortorder
"""

_ENUM_TYPE_COMMENT_QUERY = """
SELECT obj_description(pt.oid, 'pg_type') AS comment
FROM pg_type AS pt
JOIN pg_namespace AS pn ON pn.oid = pt.typnamespace
WHERE pn.nspname = %s
  AND pt.typname = %s
"""


@dataclass
class ForeignKeyInfo:
    schema: str
    table: str
    column: str


@dataclass
class ReferenceColumnInfo:
    name: str
    data_type: str
    udt_name: str
    not_null: bool
    column_default: str | None
    is_primary_key: bool
    primary_key_position: int | None
    description: str | None
    foreign_key: ForeignKeyInfo | None = None
    enum_values: list[str] = field(default_factory=list)
    enum_value_descriptions: dict[str, str] = field(default_factory=dict)


@dataclass
class ReferenceTableInfo:
    schema: str
    name: str
    description: str | None
    columns: dict[str, ReferenceColumnInfo]
    primary_key_columns: list[str]


def _parse_enum_type_comment(comment: str | None) -> dict[str, str]:
    if not comment:
        return {}
    try:
        payload = json.loads(comment)
    except json.JSONDecodeError:
        return {}
    values = payload.get("values")
    if not isinstance(values, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in values.items():
        if isinstance(key, str) and isinstance(value, str):
            result[key] = value
    return result


def get_enum_metadata(storage: PgStorage, schema: str, type_name: str) -> tuple[list[str], dict[str, str]]:
    rows_result = storage.query(_ENUM_VALUES_QUERY, params=[schema, type_name])
    values = [str(row["enumlabel"]) for row in rows_result]
    comment_row = storage.query_one(_ENUM_TYPE_COMMENT_QUERY, params=[schema, type_name])
    descriptions = _parse_enum_type_comment(comment_row.get("comment"))
    return values, descriptions


def get_reference_table_metadata(storage: PgStorage, schema: str, table: str) -> ReferenceTableInfo:
    rows_result: list[dict[str, Any]] = storage.query(_REFERENCE_TABLE_METADATA_QUERY, params=[schema, table])
    if not rows_result:
        return ReferenceTableInfo(schema=schema, name=table, description=None, columns={}, primary_key_columns=[])

    table_description = rows_result[0].get("table_description")
    columns: dict[str, ReferenceColumnInfo] = {}
    primary_key_columns: list[tuple[int, str]] = []
    enum_cache: dict[tuple[str, str], tuple[list[str], dict[str, str]]] = {}

    for row in rows_result:
        column_name = row["column_name"]
        data_type = row["data_type"]
        udt_name = row["udt_name"]
        enum_values: list[str] = []
        enum_value_descriptions: dict[str, str] = {}
        if data_type == "USER-DEFINED":
            cache_key = (schema, udt_name)
            if cache_key not in enum_cache:
                enum_cache[cache_key] = get_enum_metadata(storage, schema, udt_name)
            enum_values, enum_value_descriptions = enum_cache[cache_key]

        foreign_key: ForeignKeyInfo | None = None
        if row.get("foreign_table_schema") and row.get("foreign_table_name") and row.get("foreign_column_name"):
            foreign_key = ForeignKeyInfo(
                schema=str(row["foreign_table_schema"]),
                table=str(row["foreign_table_name"]),
                column=str(row["foreign_column_name"]),
            )

        if row["is_primary_key"] and row["primary_key_position"] is not None:
            primary_key_columns.append((int(row["primary_key_position"]), column_name))

        columns[column_name] = ReferenceColumnInfo(
            name=column_name,
            data_type=data_type,
            udt_name=udt_name,
            not_null=bool(row["not_null"]),
            column_default=row.get("column_default"),
            is_primary_key=bool(row["is_primary_key"]),
            primary_key_position=row.get("primary_key_position"),
            description=row.get("description"),
            foreign_key=foreign_key,
            enum_values=enum_values,
            enum_value_descriptions=enum_value_descriptions,
        )

    primary_key_columns.sort(key=lambda item: item[0])
    return ReferenceTableInfo(
        schema=schema,
        name=table,
        description=table_description,
        columns=columns,
        primary_key_columns=[name for _, name in primary_key_columns],
    )


def _escape_like_pattern(value: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", value)


def _column_to_text(column: sql.Identifier) -> sql.Composed:
    return sql.SQL("COALESCE({}::text, '')").format(column)


def _build_search_condition(columns: Sequence[str]) -> sql.Composed:
    if not columns:
        return sql.SQL("TRUE")
    parts = [
        sql.SQL("{} ILIKE {} ESCAPE '\\'").format(_column_to_text(sql.Identifier(name)), sql.Placeholder())
        for name in columns
    ]
    return sql.SQL(" OR ").join(parts)


@final
class ReferencesRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_table_metadata(self, schema: str, table: str) -> ReferenceTableInfo:
        return get_reference_table_metadata(self._storage, schema, table)

    def count_rows(self, schema: str, table: str, query: str, column_names: Sequence[str]) -> int:
        table_ref = sql.Identifier(schema, table)
        where_clause = sql.SQL("")
        params: list[Any] = []
        if query.strip():
            where_clause = sql.SQL("WHERE {}").format(_build_search_condition(column_names))
            pattern = f"%{_escape_like_pattern(query.strip())}%"
            params.extend([pattern] * len(column_names))

        statement = sql.SQL("SELECT COUNT(*) AS total FROM {} {}").format(table_ref, where_clause)
        row = self._storage.query_one(statement, params=params)
        return int(row["total"])

    def list_rows(
        self,
        schema: str,
        table: str,
        query: str,
        column_names: Sequence[str],
        primary_key_columns: Sequence[str],
        page: int,
        page_size: int,
    ) -> list[rows.DictRow]:
        table_ref = sql.Identifier(schema, table)
        where_clause = sql.SQL("")
        params: list[Any] = []
        if query.strip():
            where_clause = sql.SQL("WHERE {}").format(_build_search_condition(column_names))
            pattern = f"%{_escape_like_pattern(query.strip())}%"
            params.extend([pattern] * len(column_names))

        order_by = sql.SQL(", ").join(sql.Identifier(name) for name in primary_key_columns)
        params.extend([page_size, page * page_size])
        statement = sql.SQL("SELECT * FROM {} {} ORDER BY {} LIMIT %s OFFSET %s").format(
            table_ref, where_clause, order_by
        )
        return self._storage.query(statement, params=params)

    def count_reference_options(
        self,
        schema: str,
        table: str,
        query: str,
        column_names: Sequence[str],
    ) -> int:
        return self.count_rows(schema, table, query, column_names)

    def list_reference_options(
        self,
        schema: str,
        table: str,
        query: str,
        column_names: Sequence[str],
        primary_key_columns: Sequence[str],
        page: int,
        page_size: int,
    ) -> list[rows.DictRow]:
        return self.list_rows(schema, table, query, column_names, primary_key_columns, page, page_size)

    def get_row_by_key(
        self,
        schema: str,
        table: str,
        primary_key_columns: Sequence[str],
        key: dict[str, Any],
    ) -> rows.DictRow | None:
        conditions = []
        params: list[Any] = []
        for column_name in primary_key_columns:
            if column_name not in key:
                return None
            conditions.append(sql.SQL("{} = {}").format(sql.Identifier(column_name), sql.Placeholder()))
            params.append(key[column_name])

        statement = sql.SQL("SELECT * FROM {} WHERE {}").format(
            sql.Identifier(schema, table),
            sql.SQL(" AND ").join(conditions),
        )
        rows_result = self._storage.query(statement, params=params)
        if not rows_result:
            return None
        return rows_result[0]

    def foreign_key_exists(
        self,
        schema: str,
        table: str,
        column: str,
        value: Any,
    ) -> bool:
        statement = sql.SQL("SELECT 1 FROM {} WHERE {} = {} LIMIT 1").format(
            sql.Identifier(schema, table),
            sql.Identifier(column),
            sql.Placeholder(),
        )
        return bool(self._storage.query(statement, params=[value]))

    def insert_row(self, schema: str, table: str, values: dict[str, Any]) -> None:
        if not values:
            raise ValueError("insert requires at least one column")
        columns = [sql.Identifier(name) for name in values]
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in values)
        statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(schema, table),
            sql.SQL(", ").join(columns),
            placeholders,
        )
        self._storage.exec(statement, params=list(values.values()))

    def update_row(
        self,
        schema: str,
        table: str,
        primary_key_columns: Sequence[str],
        key: dict[str, Any],
        changes: dict[str, Any],
    ) -> int:
        if not changes:
            return 0

        set_parts = [
            sql.SQL("{} = {}").format(sql.Identifier(column_name), sql.Placeholder()) for column_name in changes
        ]
        where_parts = []
        params: list[Any] = list(changes.values())
        for column_name in primary_key_columns:
            where_parts.append(sql.SQL("{} = {}").format(sql.Identifier(column_name), sql.Placeholder()))
            params.append(key[column_name])

        statement = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(schema, table),
            sql.SQL(", ").join(set_parts),
            sql.SQL(" AND ").join(where_parts),
        )
        conn = self._storage.get_thread_conn()
        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute(statement, params)
                return cursor.rowcount

        with self._storage.get_pool().connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, params)
                return cursor.rowcount

    @staticmethod
    def is_unique_violation(exc: Exception) -> bool:
        return isinstance(exc, psycopg.errors.UniqueViolation)
