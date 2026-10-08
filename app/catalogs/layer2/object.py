from dataclasses import dataclass

from app.catalogs.layer2 import interface


@dataclass
class Layer2Object:
    pgc: int
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        for obj in self.data:
            if isinstance(obj, t):
                return obj
        return None
