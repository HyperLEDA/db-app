from typing import Any, Self, final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
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
    def sources(cls) -> list[Layer1Catalog]:
        return [Layer1Catalog.DESIGNATION]

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
