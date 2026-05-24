from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, final

from psycopg import sql

from app.lib.storage import postgres

_TABLE_SAMPLE_LIMIT = 50


def _description_from_param(param: Any) -> str | None:
    if param is None:
        return None
    if not isinstance(param, dict):
        return None
    d = param.get("description")
    if d is None:
        return None
    return str(d) if d != "" else None


@dataclass
class MetadataTableSummary:
    table_name: str
    description: str | None


@dataclass
class MetadataSchemaEntry:
    schema_name: str
    description: str | None
    tables: list[MetadataTableSummary]


@dataclass
class MetadataColumnDetail:
    column_name: str
    data_type: str | None
    description: str | None
    unit: str | None
    ucd: str | None


@dataclass
class MetadataTableDetail:
    schema_name: str
    table_name: str
    description: str | None
    columns: list[MetadataColumnDetail]


def _column_detail_from_row(row: dict[str, Any]) -> MetadataColumnDetail:
    param = row.get("param") or {}
    if not isinstance(param, dict):
        param = {}
    return MetadataColumnDetail(
        column_name=row["column_name"],
        data_type=row.get("data_type"),
        description=param.get("description"),
        unit=param.get("unit"),
        ucd=param.get("ucd"),
    )


@final
class MetadataRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage) -> None:
        super().__init__(storage)

    def list_schemas(self, allowed_schemas: Sequence[str]) -> list[MetadataSchemaEntry]:
        allowed = list(allowed_schemas)
        schema_rows = self._storage.query(
            "SELECT schema_name, param FROM meta.schema_info WHERE schema_name = ANY(%s) ORDER BY schema_name",
            params=[allowed],
        )
        table_rows = self._storage.query(
            "SELECT schema_name, table_name, param FROM meta.table_info "
            "WHERE schema_name = ANY(%s) ORDER BY schema_name, table_name",
            params=[allowed],
        )
        tables_by_schema: dict[str, list[MetadataTableSummary]] = {}
        for row in table_rows:
            sn = row["schema_name"]
            tables_by_schema.setdefault(sn, []).append(
                MetadataTableSummary(
                    table_name=row["table_name"],
                    description=_description_from_param(row.get("param")),
                )
            )
        return [
            MetadataSchemaEntry(
                schema_name=row["schema_name"],
                description=_description_from_param(row.get("param")),
                tables=tables_by_schema.get(row["schema_name"], []),
            )
            for row in schema_rows
        ]

    def get_table(self, schema_name: str, table_name: str) -> MetadataTableDetail | None:
        table_rows = self._storage.query(
            "SELECT param FROM meta.table_info WHERE schema_name = %s AND table_name = %s",
            params=[schema_name, table_name],
        )
        if len(table_rows) != 1:
            return None

        table_param = table_rows[0].get("param")
        table_description = _description_from_param(table_param)

        column_rows = self._storage.query(
            """
            SELECT c.column_name, c.data_type::text AS data_type, ci.param
            FROM information_schema.columns c
            INNER JOIN meta.column_info ci
              ON ci.schema_name = c.table_schema
             AND ci.table_name = c.table_name
             AND ci.column_name = c.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            params=[schema_name, table_name],
        )
        columns = [_column_detail_from_row(row) for row in column_rows]
        return MetadataTableDetail(
            schema_name=schema_name,
            table_name=table_name,
            description=table_description,
            columns=columns,
        )

    def list_tables_with_columns(
        self,
        schemas: Sequence[str],
        *,
        include_columns: bool,
    ) -> list[MetadataTableDetail]:
        if not schemas:
            return []

        table_rows = self._storage.query(
            """
            SELECT schema_name, table_name, param
            FROM meta.table_info
            WHERE schema_name = ANY(%s)
            ORDER BY schema_name, table_name
            """,
            params=[list(schemas)],
        )
        columns_by_table: dict[tuple[str, str], list[MetadataColumnDetail]] = {}
        if include_columns:
            column_rows = self._storage.query(
                """
                SELECT c.table_schema AS schema_name,
                       c.table_name,
                       c.column_name,
                       c.data_type::text AS data_type,
                       ci.param
                FROM information_schema.columns c
                INNER JOIN meta.column_info ci
                  ON ci.schema_name = c.table_schema
                 AND ci.table_name = c.table_name
                 AND ci.column_name = c.column_name
                WHERE c.table_schema = ANY(%s)
                ORDER BY c.table_schema, c.table_name, c.ordinal_position
                """,
                params=[list(schemas)],
            )
            for row in column_rows:
                key = (row["schema_name"], row["table_name"])
                columns_by_table.setdefault(key, []).append(_column_detail_from_row(row))

        return [
            MetadataTableDetail(
                schema_name=row["schema_name"],
                table_name=row["table_name"],
                description=_description_from_param(row.get("param")),
                columns=columns_by_table.get((row["schema_name"], row["table_name"]), []),
            )
            for row in table_rows
        ]

    def fetch_table_sample_rows(self, schema_name: str, table_name: str) -> list[dict[str, object]]:
        query = sql.SQL("SELECT * FROM {}.{} LIMIT {}").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
            sql.Literal(_TABLE_SAMPLE_LIMIT),
        )
        return self._storage.query(query)
