from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, final

from app.lib.storage import postgres as pg_storage


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


@dataclass
class QueryColumnMetadata:
    column_name: str
    sample_value: object | None


@dataclass
class QueryWithMetadataResult:
    columns: list[QueryColumnMetadata]
    rows: list[list[Any]]


def _infer_column_sample(column: str, rows: list[dict[str, Any]]) -> object | None:
    for row in rows:
        value = row[column]
        if value is not None:
            return value
    return None


@final
class MetadataRepository(pg_storage.TransactionalPGRepository):
    def __init__(self, storage: pg_storage.PgStorage) -> None:
        super().__init__(storage)

    def query_with_metadata(self, query: str, max_rows: int) -> QueryWithMetadataResult:
        stripped = query.strip().rstrip(";")
        wrapped = f"SELECT * FROM ({stripped}) AS _tap_sync LIMIT {max_rows}"
        dict_rows: list[dict[str, Any]] = self._storage.query(wrapped)
        if not dict_rows:
            return QueryWithMetadataResult(columns=[], rows=[])
        col_names = list(dict_rows[0].keys())
        columns = [
            QueryColumnMetadata(column_name=name, sample_value=_infer_column_sample(name, dict_rows))
            for name in col_names
        ]
        result_rows = [[row[name] for name in col_names] for row in dict_rows]
        return QueryWithMetadataResult(columns=columns, rows=result_rows)

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
