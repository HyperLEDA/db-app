from dataclasses import dataclass, field
from typing import Any

from app.lib.storage.postgres.postgres_storage import PgStorage

_TABLE_METADATA_QUERY = """
WITH t AS (
  SELECT %s::text AS schema_name, %s::text AS table_name
)
SELECT
  c.column_name,
  c.data_type::text AS data_type,
  (c.is_nullable = 'NO') AS not_null,
  (pk.column_name IS NOT NULL) AS is_primary_key,
  ti.param->>'description' AS table_description,
  ci.param->>'description' AS description,
  ci.param->>'unit' AS unit,
  ci.param->>'ucd' AS ucd
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
  SELECT kcu.column_name
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
"""


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    description: str | None = None
    unit: str | None = None
    ucd: str | None = None
    not_null: bool = False


@dataclass
class TableInfo:
    schema: str
    name: str
    description: str | None = None
    columns: dict[str, ColumnInfo] = field(default_factory=dict)
    primary_keys: set[str] = field(default_factory=set)


def get_table_metadata(storage: PgStorage, schema: str, table: str) -> TableInfo:
    rows: list[dict[str, Any]] = storage.query(_TABLE_METADATA_QUERY, params=[schema, table])
    if not rows:
        return TableInfo(schema=schema, name=table, description=None, columns={}, primary_keys=set())

    table_description = rows[0].get("table_description")
    columns: dict[str, ColumnInfo] = {}
    primary_keys: set[str] = set()
    for row in rows:
        column_name = row["column_name"]
        if row["is_primary_key"]:
            primary_keys.add(column_name)
        columns[column_name] = ColumnInfo(
            name=column_name,
            data_type=row["data_type"],
            description=row.get("description"),
            unit=row.get("unit"),
            ucd=row.get("ucd"),
            not_null=bool(row["not_null"]),
        )

    return TableInfo(
        schema=schema,
        name=table,
        description=table_description,
        columns=columns,
        primary_keys=primary_keys,
    )
