from dataclasses import dataclass
from typing import Any

from app.domain.homogenization import column_filters, table_filters


@dataclass
class Rule:
    catalog: str
    parameter: str
    key: str
    column_filters: column_filters.ColumnFilter
    table_filters: table_filters.TableFilter
    priority: int


@dataclass
class Params:
    catalog: str
    key: str
    params: dict[str, Any]
