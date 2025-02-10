from dataclasses import dataclass
from typing import Any

from app.data.model import interface
from app.lib.storage import enums


@dataclass
class Layer0Object:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: list[interface.CatalogObject]
    pgc: int | None = None
