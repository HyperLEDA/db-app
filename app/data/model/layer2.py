from dataclasses import dataclass

from app.data.model import interface


@dataclass
class Layer2CatalogObject:
    pgc: int
    catalog_object: interface.CatalogObject


@dataclass
class Layer2Object:
    pgc: int
    data: list[interface.CatalogObject]
