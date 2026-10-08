from typing import Any, Self, final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class DesignationCatalogObject(interface.CatalogObject):
    def __init__(self, design: str) -> None:
        self.designation = design

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.DESIGNATION

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.designation"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.DESIGNATION]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["design"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {"design": self.designation}

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(design=data["design"])
