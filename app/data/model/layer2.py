from dataclasses import dataclass

from app.data.model import common


@dataclass
class Layer2CatalogObject:
    pgc: int
    catalog_object: common.CatalogObject
