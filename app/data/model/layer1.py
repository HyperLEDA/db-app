import enum
from dataclasses import dataclass


@dataclass
class Layer1CatalogObject:
    pgc: int
    object_id: str
    data: dict


class Layer1Catalog(enum.Enum):
    ICRS = "icrs"
    DESIGNATION = "designation"
