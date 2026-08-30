from dataclasses import dataclass
from typing import Any


@dataclass
class QueryColumnMetadata:
    column_name: str
    sample_value: object | None


@dataclass
class QueryWithMetadataResult:
    columns: list[QueryColumnMetadata]
    rows: list[list[Any]]
