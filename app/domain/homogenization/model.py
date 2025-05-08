from dataclasses import dataclass
from typing import Any

from app.data import model
from app.domain.homogenization import filters


@dataclass
class Rule:
    catalog: model.RawCatalog
    parameter: str
    filter: filters.ColumnFilter
    key: str = ""
    priority: int = 2**32


@dataclass
class Params:
    catalog: model.RawCatalog
    key: str
    params: dict[str, Any]
