from dataclasses import dataclass
from typing import Any

import pandas

from app.data.model import interface
from app.lib.storage import enums


@dataclass
class Layer0OldObject:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: list[interface.CatalogObject]
    pgc: int | None = None


@dataclass
class Layer0RawData:
    table_id: int
    data: pandas.DataFrame


@dataclass
class Layer0Object:
    object_id: int
    data: list[interface.CatalogObject]
