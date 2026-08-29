from dataclasses import dataclass

from app.data.model import interface


@dataclass
class Layer2CatalogObject:
    pgc: int
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        return interface.get_object(self.data, t)
