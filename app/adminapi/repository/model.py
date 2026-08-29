from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnSchemaInfo:
    name: str
    description: str | None
    unit: str | None
    ucd: str | None


@dataclass
class TableSchemaInfo:
    table_description: str
    columns: list[ColumnSchemaInfo]


@dataclass
class QueryColumnMetadata:
    column_name: str
    sample_value: object | None


@dataclass
class QueryWithMetadataResult:
    columns: list[QueryColumnMetadata]
    rows: list[list[Any]]
