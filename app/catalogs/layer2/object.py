from dataclasses import dataclass

from app.catalogs import interface as catalogs_interface
from app.catalogs.layer2 import interface


@dataclass
class Layer2Object:
    pgc: int
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        return catalogs_interface.get_object(self.data, t)
