from dataclasses import dataclass
from typing import Any

from app.data.model import common
from app.lib.storage import enums


@dataclass
class Layer0CatalogObject:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: list[common.CatalogObject]
    pgc: int | None = None
