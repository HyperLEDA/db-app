from dataclasses import dataclass

from app.data.model import interface


@dataclass
class Layer1CatalogObject:
    pgc: int
    object_id: str
    catalog_object: interface.CatalogObject
