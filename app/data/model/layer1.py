from dataclasses import dataclass


@dataclass
class Layer1CatalogObject:
    pgc: int
    object_id: str
    data: dict
