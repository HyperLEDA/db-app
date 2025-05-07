from dataclasses import dataclass
from typing import Any

from app.domain.homogenization import filters


@dataclass
class Rule:
    catalog: str
    parameter: str
    key: str
    column_filters: filters.ColumnFilter
    priority: int


@dataclass
class Params:
    catalog: str
    key: str
    params: dict[str, Any]
