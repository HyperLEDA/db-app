from typing import Any, Self, final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class NatureCatalogObject(interface.CatalogObject):
    def __init__(self, type_name: str) -> None:
        self.type_name = type_name

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.NATURE

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.nature"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.NATURE]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["type_name"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {"type_name": self.type_name}

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(type_name=data["type_name"])
